interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
}

export default function Toggle({ checked, onChange, label, disabled = false }: ToggleProps) {
  return (
    <div className="flex items-center gap-3">
      <label className={`relative inline-flex items-center ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only peer"
        />
        <div className="w-9 h-5 bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-full peer peer-checked:bg-emerald-500 peer-checked:border-emerald-500 transition-colors duration-200 after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-transform after:duration-200 peer-checked:after:translate-x-4" />
      </label>
      {label && <span className="text-sm text-[var(--text-primary)]">{label}</span>}
    </div>
  )
}
