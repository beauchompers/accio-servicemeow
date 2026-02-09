import { useState, useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'
import { Loader2 } from 'lucide-react'
import { useUploadEditorImage } from '@/hooks/useTickets'

interface EditorImagePopoverProps {
  editor: Editor
  anchorRef: React.RefObject<HTMLButtonElement | null>
  onClose: () => void
}

export function EditorImagePopover({ editor, anchorRef, onClose }: EditorImagePopoverProps) {
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const upload = useUploadEditorImage()

  // Close on Escape or click outside
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    function handleClickOutside(e: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        anchorRef.current &&
        !anchorRef.current.contains(e.target as Node)
      ) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose, anchorRef])

  async function handleFileSelect(file: File) {
    setError(null)
    try {
      const result = await upload.mutateAsync(file)
      editor.chain().focus().setImage({ src: result.url }).run()
      onClose()
    } catch {
      setError('Upload failed. Please try again.')
    }
  }

  return (
    <div
      ref={popoverRef}
      className="absolute z-50 mt-1 w-72 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] shadow-lg p-3"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFileSelect(file)
        }}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={upload.isPending}
        className="w-full flex items-center justify-center gap-2 rounded border border-dashed border-[var(--border)] bg-[var(--bg-secondary)] py-6 text-sm text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--text-primary)] transition-colors disabled:opacity-50"
      >
        {upload.isPending ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Uploading…
          </>
        ) : (
          'Click to browse…'
        )}
      </button>
      {error && (
        <p className="mt-2 text-xs text-red-400">{error}</p>
      )}
      <div className="flex justify-end mt-3">
        <button
          type="button"
          onClick={onClose}
          className="px-2.5 py-1 text-xs rounded text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
