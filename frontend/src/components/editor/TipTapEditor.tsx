import { useState, useRef, useEffect } from 'react'
import { useEditor, EditorContent, type Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { common, createLowlight } from 'lowlight'
import {
  Bold,
  Italic,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Code,
  ImageIcon,
  Link as LinkIcon,
  Undo,
  Redo,
} from 'lucide-react'

import { EditorLinkPopover } from '@/components/editor/EditorLinkPopover'
import { EditorImagePopover } from '@/components/editor/EditorImagePopover'
import '@/components/editor/editor-styles.css'

const lowlight = createLowlight(common)

interface TipTapEditorProps {
  content?: string
  onChange?: (html: string) => void
  editable?: boolean
  placeholder?: string
  className?: string
}

interface ToolbarButtonProps {
  onClick: () => void
  isActive?: boolean
  children: React.ReactNode
  title: string
  buttonRef?: React.Ref<HTMLButtonElement>
}

function ToolbarButton({ onClick, isActive, children, title, buttonRef }: ToolbarButtonProps) {
  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={onClick}
      title={title}
      className={[
        'p-1.5 rounded transition-colors duration-150',
        isActive
          ? 'bg-[var(--accent)]/20 text-[var(--accent)]'
          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

function ToolbarSeparator() {
  return <div className="w-px h-5 bg-[var(--border)] mx-1" />
}

function Toolbar({ editor }: { editor: Editor }) {
  const [showLinkPopover, setShowLinkPopover] = useState(false)
  const [showImagePopover, setShowImagePopover] = useState(false)
  const linkBtnRef = useRef<HTMLButtonElement>(null)
  const imageBtnRef = useRef<HTMLButtonElement>(null)

  return (
    <div className="flex items-center gap-0.5 p-2 border-b border-[var(--border)] flex-wrap">
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        isActive={editor.isActive('bold')}
        title="Bold"
      >
        <Bold size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        isActive={editor.isActive('italic')}
        title="Italic"
      >
        <Italic size={18} />
      </ToolbarButton>

      <ToolbarSeparator />

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        isActive={editor.isActive('heading', { level: 1 })}
        title="Heading 1"
      >
        <Heading1 size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        isActive={editor.isActive('heading', { level: 2 })}
        title="Heading 2"
      >
        <Heading2 size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        isActive={editor.isActive('heading', { level: 3 })}
        title="Heading 3"
      >
        <Heading3 size={18} />
      </ToolbarButton>

      <ToolbarSeparator />

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        isActive={editor.isActive('bulletList')}
        title="Bullet List"
      >
        <List size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        isActive={editor.isActive('orderedList')}
        title="Ordered List"
      >
        <ListOrdered size={18} />
      </ToolbarButton>

      <ToolbarSeparator />

      <ToolbarButton
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        isActive={editor.isActive('codeBlock')}
        title="Code Block"
      >
        <Code size={18} />
      </ToolbarButton>

      <div className="relative">
        <ToolbarButton
          buttonRef={imageBtnRef}
          onClick={() => {
            setShowLinkPopover(false)
            setShowImagePopover((prev) => !prev)
          }}
          title="Insert Image"
        >
          <ImageIcon size={18} />
        </ToolbarButton>
        {showImagePopover && (
          <EditorImagePopover
            editor={editor}
            anchorRef={imageBtnRef}
            onClose={() => setShowImagePopover(false)}
          />
        )}
      </div>

      <div className="relative">
        <ToolbarButton
          buttonRef={linkBtnRef}
          onClick={() => {
            setShowImagePopover(false)
            setShowLinkPopover((prev) => !prev)
          }}
          isActive={editor.isActive('link')}
          title="Insert Link"
        >
          <LinkIcon size={18} />
        </ToolbarButton>
        {showLinkPopover && (
          <EditorLinkPopover
            editor={editor}
            anchorRef={linkBtnRef}
            onClose={() => setShowLinkPopover(false)}
          />
        )}
      </div>

      <ToolbarSeparator />

      <ToolbarButton
        onClick={() => editor.chain().focus().undo().run()}
        title="Undo"
      >
        <Undo size={18} />
      </ToolbarButton>

      <ToolbarButton
        onClick={() => editor.chain().focus().redo().run()}
        title="Redo"
      >
        <Redo size={18} />
      </ToolbarButton>
    </div>
  )
}

export function TipTapEditor({
  content,
  onChange,
  editable = true,
  placeholder: placeholderText,
  className,
}: TipTapEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        codeBlock: false,
      }),
      CodeBlockLowlight.configure({
        lowlight,
      }),
      Image.configure({
        allowBase64: true,
        inline: false,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-[var(--accent)] underline',
        },
      }),
      Placeholder.configure({
        placeholder: placeholderText,
      }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML())
    },
    editorProps: {
      attributes: {
        class: 'focus:outline-none min-h-[120px] p-4 text-[var(--text-primary)]',
      },
    },
  })

  // Sync editor when content is cleared externally (e.g. after posting a note)
  useEffect(() => {
    if (editor && content === '' && editor.getHTML() !== '<p></p>') {
      editor.commands.setContent('')
    }
  }, [editor, content])

  if (!editor) return null

  return (
    <div
      className={[
        'tiptap-editor border border-[var(--border)] rounded-lg overflow-hidden bg-[var(--bg-secondary)]',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {editable && <Toolbar editor={editor} />}
      <EditorContent editor={editor} />
    </div>
  )
}

export default TipTapEditor
