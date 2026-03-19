/**
 * Supabase client — connects to your Supabase project for
 * real-time subscriptions and auth.
 *
 * Security: tokens are stored in sessionStorage (not localStorage) so they
 * are automatically cleared when the browser tab is closed, significantly
 * reducing the window for XSS token-theft attacks.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: window.sessionStorage,
    storageKey: 'keen-auth',
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
});

export default supabase;
