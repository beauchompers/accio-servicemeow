import { useState } from 'react'
import { Plus, Key, Copy, Check, AlertTriangle, Trash2 } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from '@/hooks/useApiKeys'
import { relativeTime } from '@/utils/format'
import type { ApiKeyCreateResponse } from '@/types'

// ─── API Keys Page ──────────────────────────────────────────────────────────

export default function ApiKeys() {
  const toast = useToast()
  const { data, isLoading, isError } = useApiKeys()
  const createApiKey = useCreateApiKey()
  const revokeApiKey = useRevokeApiKey()

  // ─── Inline form state ──────────────────────────────────────────────────
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createdKey, setCreatedKey] = useState<ApiKeyCreateResponse | null>(null)
  const [revokingKeyId, setRevokingKeyId] = useState<string | null>(null)
  const [keyName, setKeyName] = useState('')
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [copied, setCopied] = useState(false)

  // ─── Handlers ──────────────────────────────────────────────────────────

  function openCreateForm() {
    setKeyName('')
    setCreatedKey(null)
    setFormErrors({})
    setCopied(false)
    setShowCreateForm(true)
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()

    const errors: Record<string, string> = {}
    if (!keyName.trim()) errors.name = 'Key name is required.'
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }
    setFormErrors({})

    try {
      const result = await createApiKey.mutateAsync({ name: keyName.trim() })
      setCreatedKey(result)
      toast.success('API key generated successfully.')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to generate API key.'
      toast.error(message)
    }
  }

  async function handleCopyKey() {
    if (!createdKey) return
    try {
      await navigator.clipboard.writeText(createdKey.plain_key)
      setCopied(true)
      toast.success('Key copied to clipboard.')
      setTimeout(() => setCopied(false), 3000)
    } catch {
      toast.error('Failed to copy to clipboard.')
    }
  }

  async function handleRevoke() {
    if (!revokingKeyId) return

    try {
      await revokeApiKey.mutateAsync(revokingKeyId)
      toast.success('API key revoked successfully.')
      setRevokingKeyId(null)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to revoke API key.'
      toast.error(message)
    }
  }

  const apiKeys = data ?? []

  // ─── Loading state ─────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div>
        <PageHeader title="API Keys" description="Manage API keys for programmatic access." />
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      </div>
    )
  }

  // ─── Error state ───────────────────────────────────────────────────────

  if (isError) {
    return (
      <div>
        <PageHeader title="API Keys" description="Manage API keys for programmatic access." />
        <EmptyState
          icon={<Key size={40} />}
          title="Failed to load API keys"
          description="An error occurred while fetching API key data. Please try again."
        />
      </div>
    )
  }

  // ─── Render ────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="API Keys"
        description="Manage API keys for programmatic access."
        actions={
          <Button variant="primary" size="sm" onClick={openCreateForm}>
            <Plus size={16} />
            Generate Key
          </Button>
        }
      />

      {/* ─── Inline Create Form ──────────────────────────────────────────────── */}
      {showCreateForm && (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 mb-4">
          {createdKey ? (
            <div className="space-y-4">
              {/* Warning */}
              <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/25">
                <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
                <p className="text-sm text-amber-400">
                  This key will only be shown once. Make sure to copy it now and store it securely.
                </p>
              </div>

              {/* Key display */}
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Name
                </label>
                <p className="text-sm text-[var(--text-secondary)]">{createdKey.name}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  API Key
                </label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)] text-sm font-mono text-[var(--text-primary)] break-all select-all">
                    {createdKey.plain_key}
                  </code>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleCopyKey}
                  >
                    {copied ? (
                      <Check size={16} className="text-emerald-400" />
                    ) : (
                      <Copy size={16} />
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex justify-end">
                <Button type="button" variant="primary" onClick={() => setShowCreateForm(false)}>
                  Done
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreate}>
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Key Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g. CI/CD Pipeline, External Integration"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {formErrors.name && <p className="text-sm text-red-400 mt-1">{formErrors.name}</p>}
                <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
                  A descriptive name to identify this API key.
                </p>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <Button type="button" variant="secondary" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  loading={createApiKey.isPending}
                  type="submit"
                >
                  <Key size={16} />
                  Generate
                </Button>
              </div>
            </form>
          )}
        </div>
      )}

      {apiKeys.length === 0 ? (
        <EmptyState
          icon={<Key size={40} />}
          title="No API keys"
          description="Generate your first API key for programmatic access to the platform."
          action={
            <Button variant="primary" size="sm" onClick={openCreateForm}>
              <Plus size={16} />
              Generate Key
            </Button>
          }
        />
      ) : (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Name</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Key Prefix</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Created</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Last Used</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Status</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map((apiKey) => (
                <tr
                  key={apiKey.id}
                  className={[
                    'border-b border-[var(--border)] transition-colors duration-150',
                    apiKey.is_active
                      ? 'hover:bg-[var(--bg-tertiary)]'
                      : 'opacity-50',
                  ].join(' ')}
                >
                  <td className="px-4 py-3 text-sm text-[var(--text-primary)] font-medium">
                    {apiKey.name}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <code className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-secondary)] font-mono text-xs">
                      {apiKey.key_prefix}...
                    </code>
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                    {relativeTime(apiKey.created_at)}
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                    {apiKey.last_used_at ? relativeTime(apiKey.last_used_at) : 'Never'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {apiKey.is_active ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-400 border border-red-500/25">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        Revoked
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {apiKey.is_active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setRevokingKeyId(apiKey.id)}
                      >
                        <Trash2 size={14} className="text-red-400" />
                        Revoke
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ─── Revoke Confirmation Modal ──────────────────────────────────────── */}
      <Modal
        isOpen={!!revokingKeyId}
        onClose={() => setRevokingKeyId(null)}
        title="Revoke API Key"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRevokingKeyId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={revokeApiKey.isPending}
              onClick={handleRevoke}
            >
              <Trash2 size={16} />
              Revoke Key
            </Button>
          </>
        }
      >
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-full bg-red-500/10">
            <AlertTriangle size={20} className="text-red-400" />
          </div>
          <div>
            <p className="text-sm text-[var(--text-primary)]">
              Are you sure you want to revoke this API key?
            </p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              This action cannot be undone. Any applications or services using this key will immediately lose access.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  )
}
