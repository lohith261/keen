/**
 * Unit tests for apiClient.ts
 *
 * Key regressions guarded:
 * 1. engagementsApi.restart sends body as an object (not a double-stringified string)
 * 2. ApiError parses FastAPI 422 validation arrays correctly
 * 3. getAuthToken reads from sessionStorage['keen-auth'] first
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// We test the internal request() logic by intercepting fetch.
// The module uses import.meta.env which Vitest provides as empty strings by default.

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Re-import module after stubbing globals
const { engagementsApi, ApiError } = await import('../apiClient');

function makeOkResponse(body: unknown) {
  return {
    ok: true,
    json: () => Promise.resolve(body),
    status: 200,
  } as unknown as Response;
}

function makeErrorResponse(status: number, body: unknown) {
  return {
    ok: false,
    status,
    statusText: 'Error',
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

beforeEach(() => {
  mockFetch.mockReset();
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('engagementsApi.restart', () => {
  it('sends body as a JSON object (not double-stringified)', async () => {
    // demo mode: localStorage missing key → isDemoMode() returns true
    mockFetch.mockResolvedValueOnce(makeOkResponse({ id: '123', status: 'running' }));

    await engagementsApi.restart('abc-123');

    expect(mockFetch).toHaveBeenCalledOnce();
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];

    // The body must be a valid JSON string that decodes to an object
    expect(typeof init.body).toBe('string');
    const parsed = JSON.parse(init.body as string);
    expect(typeof parsed).toBe('object');
    expect(parsed).toHaveProperty('demo_mode');

    // Double-stringify would produce a string-within-string: '"{\\"demo_mode\\":..."'
    // Ensure the body string starts with '{' not '"'
    expect((init.body as string).trimStart()[0]).toBe('{');
  });

  it('includes Content-Type: application/json header', async () => {
    mockFetch.mockResolvedValueOnce(makeOkResponse({}));
    await engagementsApi.restart('abc-123');
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
  });
});

describe('ApiError', () => {
  it('parses FastAPI 422 validation error array into readable detail', async () => {
    mockFetch.mockResolvedValueOnce(
      makeErrorResponse(422, {
        detail: [
          { loc: ['body', 'company_name'], msg: 'field required' },
          { loc: ['body', 'config'], msg: 'value is not a valid dict' },
        ],
      })
    );

    let caught: Error | null = null;
    try {
      await engagementsApi.create({ company_name: '' });
    } catch (e) {
      caught = e as Error;
    }

    expect(caught).not.toBeNull();
    expect(caught!.message).toContain('422');
    // Should join both validation errors
    expect(caught!.message).toContain('company_name');
    expect(caught!.message).toContain('config');
  });

  it('handles plain string detail', async () => {
    mockFetch.mockResolvedValueOnce(
      makeErrorResponse(404, { detail: 'Engagement not found' })
    );

    let caught: Error | null = null;
    try {
      await engagementsApi.get('nonexistent');
    } catch (e) {
      caught = e as Error;
    }

    expect(caught!.message).toContain('Engagement not found');
  });
});

describe('getAuthToken (via Authorization header)', () => {
  it('sends Authorization header when token in sessionStorage', async () => {
    sessionStorage.setItem('keen-auth', JSON.stringify({ access_token: 'test-jwt-token' }));
    mockFetch.mockResolvedValueOnce(makeOkResponse([]));

    await engagementsApi.list();

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer test-jwt-token');
  });

  it('sends no Authorization header when no token stored', async () => {
    mockFetch.mockResolvedValueOnce(makeOkResponse([]));

    await engagementsApi.list();

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers['Authorization']).toBeUndefined();
  });
});
