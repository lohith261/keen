import { useCallback, useEffect, useRef, useState } from 'react';
import {
  FileText, FileSpreadsheet, Presentation, Upload, Trash2, AlertCircle,
  CheckCircle2, Loader2, X,
} from 'lucide-react';
import { documentsApi, type DocumentRecord } from '../../lib/apiClient';

interface Props {
  engagementId: string;
  readOnly?: boolean;
}

const ACCEPTED = '.pdf,.xlsx,.xls,.pptx,.ppt,.docx,.doc,.csv,.txt';
const MAX_MB = 50;

function fileIcon(fileType: string) {
  if (fileType === 'xlsx') return <FileSpreadsheet className="w-4 h-4 text-green-400" />;
  if (fileType === 'pptx') return <Presentation className="w-4 h-4 text-orange-400" />;
  return <FileText className="w-4 h-4 text-blue-400" />;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsPanel({ engagementId, readOnly = false }: Props) {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadDocs = useCallback(async () => {
    try {
      const list = await documentsApi.list(engagementId);
      setDocs(list);
    } catch {
      // silent — table may not exist yet in dev
    } finally {
      setLoading(false);
    }
  }, [engagementId]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadError(null);

    const fileArray = Array.from(files);
    const oversized = fileArray.find((f) => f.size > MAX_MB * 1024 * 1024);
    if (oversized) {
      setUploadError(`"${oversized.name}" exceeds ${MAX_MB} MB limit`);
      return;
    }

    setUploading(true);
    const errors: string[] = [];
    for (const file of fileArray) {
      try {
        const doc = await documentsApi.upload(engagementId, file);
        setDocs((prev) => [doc, ...prev]);
      } catch (err: unknown) {
        errors.push(`${file.name}: ${err instanceof Error ? err.message : 'failed'}`);
      }
    }
    if (errors.length > 0) setUploadError(errors.join(' · '));
    setUploading(false);
  };

  const handleDelete = async (docId: string) => {
    setDeletingId(docId);
    try {
      await documentsApi.delete(engagementId, docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
    } catch {
      // ignore
    } finally {
      setDeletingId(null);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Documents</h3>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            {readOnly
              ? 'Uploaded documents are included in the analysis pipeline'
              : 'Upload documents to include in the pipeline — PDF, Excel, PowerPoint, Word, CSV'}
          </p>
        </div>
      </div>

      {/* Drop zone */}
      {!readOnly && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? 'border-theme-text/60 bg-theme-border/30'
              : 'border-theme-border hover:border-theme-text/30 hover:bg-theme-border/10'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-theme-text-muted" />
              <p className="text-xs font-mono text-theme-text-muted">Uploading…</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-6 h-6 text-theme-text-muted" />
              <p className="text-xs font-mono text-theme-text-muted">
                Drop files here or <span className="underline">click to browse</span>
              </p>
              <p className="text-[10px] font-mono text-theme-text-muted/60">
                PDF · Excel · PowerPoint · Word · CSV · TXT · max {MAX_MB} MB
              </p>
            </div>
          )}
        </div>
      )}

      {uploadError && (
        <div className="flex items-center gap-2 text-xs text-red-400 font-mono">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {uploadError}
          <button onClick={() => setUploadError(null)} className="ml-auto">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Document list */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-theme-text-muted" />
        </div>
      )}

      {!loading && docs.length === 0 && (
        <div className="border border-dashed border-theme-border rounded-xl p-8 text-center">
          <FileText className="w-6 h-6 text-theme-text-muted mx-auto mb-2" />
          <p className="text-xs font-mono text-theme-text-muted">
            {readOnly ? 'No documents were uploaded for this engagement' : 'No documents yet'}
          </p>
        </div>
      )}

      {!loading && docs.length > 0 && (
        <div className="space-y-2">
          {docs.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 px-4 py-3 border border-theme-border rounded-xl"
            >
              {fileIcon(doc.file_type)}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate">{doc.filename}</p>
                <p className="text-[10px] font-mono text-theme-text-muted">
                  {formatBytes(doc.file_size_bytes)}
                  {doc.page_count ? ` · ${doc.page_count} pages` : ''}
                  {' · '}
                  <span className="uppercase">{doc.file_type}</span>
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {doc.status === 'processing' && (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    PROCESSING
                  </span>
                )}
                {doc.status === 'ready' && (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-green-400">
                    <CheckCircle2 className="w-3 h-3" />
                    READY
                  </span>
                )}
                {doc.status === 'error' && (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-red-400">
                    <AlertCircle className="w-3 h-3" />
                    ERROR
                  </span>
                )}
                {!readOnly && (
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-theme-text-muted hover:text-red-400 transition-colors disabled:opacity-40"
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
