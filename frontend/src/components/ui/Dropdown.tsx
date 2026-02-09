import { useState, useRef, useEffect, useCallback, type ReactNode } from 'react'
import { ChevronDown, Search, Check } from 'lucide-react'

// ─── Types ──────────────────────────────────────────────────────────────────

interface DropdownOption {
  value: string
  label: string
}

interface DropdownBaseProps {
  options: DropdownOption[]
  placeholder?: string
  searchable?: boolean
  disabled?: boolean
  className?: string
}

interface SingleDropdownProps extends DropdownBaseProps {
  multiple?: false
  value: string
  onChange: (value: string) => void
}

interface MultiDropdownProps extends DropdownBaseProps {
  multiple: true
  value: string[]
  onChange: (value: string[]) => void
}

type DropdownProps = SingleDropdownProps | MultiDropdownProps

// ─── Component ──────────────────────────────────────────────────────────────

export default function Dropdown(props: DropdownProps) {
  const {
    options,
    placeholder = 'Select...',
    searchable = false,
    multiple = false,
    disabled = false,
    className = '',
  } = props

  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  // Close on outside click
  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (
      containerRef.current &&
      !containerRef.current.contains(e.target as Node)
    ) {
      setIsOpen(false)
      setSearch('')
    }
  }, [])

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [handleClickOutside])

  useEffect(() => {
    if (isOpen && searchable) {
      searchRef.current?.focus()
    }
  }, [isOpen, searchable])

  const filteredOptions = search
    ? options.filter((o) =>
        o.label.toLowerCase().includes(search.toLowerCase()),
      )
    : options

  // ─── Trigger label ──────────────────────────────────────────────────────

  let triggerLabel: ReactNode

  if (multiple && props.multiple) {
    const selected = props.value
    if (selected.length === 0) {
      triggerLabel = (
        <span className="text-[var(--text-secondary)]">{placeholder}</span>
      )
    } else if (selected.length === 1) {
      const match = options.find((o) => o.value === selected[0])
      triggerLabel = match?.label ?? selected[0]
    } else {
      triggerLabel = `${selected.length} selected`
    }
  } else if (!multiple && !props.multiple) {
    const match = options.find((o) => o.value === props.value)
    triggerLabel = match ? (
      match.label
    ) : (
      <span className="text-[var(--text-secondary)]">{placeholder}</span>
    )
  }

  // ─── Select handler ─────────────────────────────────────────────────────

  function handleSelect(optionValue: string) {
    if (multiple && props.multiple) {
      const current = props.value
      const next = current.includes(optionValue)
        ? current.filter((v) => v !== optionValue)
        : [...current, optionValue]
      props.onChange(next)
    } else if (!props.multiple) {
      props.onChange(optionValue)
      setIsOpen(false)
      setSearch('')
    }
  }

  function isSelected(optionValue: string): boolean {
    if (multiple && props.multiple) {
      return props.value.includes(optionValue)
    }
    if (!props.multiple) {
      return props.value === optionValue
    }
    return false
  }

  // ─── Render ─────────────────────────────────────────────────────────────

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((o) => !o)}
        className={[
          'flex items-center justify-between gap-2 w-full rounded-lg border px-3 py-2 text-sm',
          'bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]',
          'hover:bg-[var(--border)] transition-all duration-200',
          'disabled:opacity-50 disabled:cursor-not-allowed',
        ].join(' ')}
      >
        <span className="truncate">{triggerLabel}</span>
        <ChevronDown
          size={16}
          className={[
            'shrink-0 text-[var(--text-secondary)] transition-transform duration-200',
            isOpen ? 'rotate-180' : '',
          ].join(' ')}
        />
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] shadow-lg overflow-hidden">
          {/* Search */}
          {searchable && (
            <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border)]">
              <Search size={14} className="text-[var(--text-secondary)] shrink-0" />
              <input
                ref={searchRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] outline-none"
              />
            </div>
          )}

          {/* Options */}
          <ul className="max-h-60 overflow-y-auto py-1">
            {filteredOptions.length === 0 ? (
              <li className="px-3 py-2 text-sm text-[var(--text-secondary)]">
                No options found
              </li>
            ) : (
              filteredOptions.map((option) => {
                const selected = isSelected(option.value)
                return (
                  <li key={option.value}>
                    <button
                      type="button"
                      onClick={() => handleSelect(option.value)}
                      className={[
                        'flex items-center gap-2 w-full px-3 py-2 text-sm text-left',
                        'transition-all duration-200',
                        selected
                          ? 'bg-[var(--accent)]/10 text-[var(--accent)]'
                          : 'text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
                      ].join(' ')}
                    >
                      {multiple && (
                        <div
                          className={[
                            'flex items-center justify-center w-4 h-4 rounded border shrink-0',
                            selected
                              ? 'bg-[var(--accent)] border-[var(--accent)]'
                              : 'border-[var(--border)]',
                          ].join(' ')}
                        >
                          {selected && (
                            <Check size={12} className="text-white" />
                          )}
                        </div>
                      )}
                      <span className="truncate">{option.label}</span>
                    </button>
                  </li>
                )
              })
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
