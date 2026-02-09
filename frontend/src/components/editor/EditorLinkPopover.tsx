import { useState, useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'

interface EditorLinkPopoverProps {
  editor: Editor
  anchorRef: React.RefObject<HTMLButtonElement | null>
  onClose: () => void
}

export function EditorLinkPopover({ editor, anchorRef, onClose }: EditorLinkPopoverProps) {
  const existingHref = editor.getAttributes('link').href as string | undefined
  const [url, setUrl] = useState(existingHref ?? '')
  const inputRef = useRef<HTMLInputElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

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

  const isValid = url.startsWith('http://') || url.startsWith('https://')

  function handleInsert() {
    if (!isValid) return
    editor.chain().focus().setLink({ href: url }).run()
    onClose()
  }

  function handleRemove() {
    editor.chain().focus().unsetLink().run()
    onClose()
  }

  return (
    <div
      ref={popoverRef}
      className="absolute z-50 mt-1 w-72 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] shadow-lg p-3"
    >
      <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
        URL
      </label>
      <input
        ref={inputRef}
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && isValid) handleInsert()
        }}
        placeholder="https://..."
        className="w-full rounded border border-[var(--border)] bg-[var(--bg-secondary)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
      />
      <div className="flex items-center justify-between mt-3">
        <div>
          {existingHref && (
            <button
              type="button"
              onClick={handleRemove}
              className="text-xs text-red-400 hover:text-red-300 transition-colors"
            >
              Remove link
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-2.5 py-1 text-xs rounded text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleInsert}
            disabled={!isValid}
            className="px-2.5 py-1 text-xs rounded bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Insert
          </button>
        </div>
      </div>
    </div>
  )
}
