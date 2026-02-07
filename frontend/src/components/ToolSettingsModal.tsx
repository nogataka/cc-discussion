import { useState, useEffect } from 'react'
import { Settings, Check, X } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog'
import { Button } from './ui/button'
import { api, ToolPermissionMode, ToolPermissions } from '../lib/api'

interface ToolSettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ToolSettingsModal({ isOpen, onClose }: ToolSettingsModalProps) {
  const [mode, setMode] = useState<ToolPermissionMode>('read_only')
  const [permissions, setPermissions] = useState<ToolPermissions | null>(null)
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)

  useEffect(() => {
    if (isOpen) {
      loadSettings()
    }
  }, [isOpen])

  const loadSettings = async () => {
    setInitialLoading(true)
    try {
      const [settings, perms] = await Promise.all([
        api.settings.get(),
        api.settings.getToolPermissions(),
      ])
      setMode(settings.tool_permission_mode)
      setPermissions(perms)
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setInitialLoading(false)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      await api.settings.update({ tool_permission_mode: mode })
      onClose()
    } catch (error) {
      console.error('Failed to save settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const renderToolTable = (
    title: string,
    readOnlyTools: string[],
    allTools: string[]
  ) => (
    <div className="border rounded-lg p-3">
      <h4 className="font-medium mb-2">{title}</h4>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-1">ツール</th>
            <th className="text-center py-1 w-24">読み専用</th>
            <th className="text-center py-1 w-24">システム</th>
          </tr>
        </thead>
        <tbody>
          {allTools.map(tool => (
            <tr key={tool} className="border-b last:border-0">
              <td className="py-1.5 font-mono text-xs">{tool}</td>
              <td className="text-center">
                {readOnlyTools.includes(tool) ? (
                  <Check className="h-4 w-4 text-green-600 mx-auto" />
                ) : (
                  <X className="h-4 w-4 text-red-500 mx-auto" />
                )}
              </td>
              <td className="text-center">
                <Check className="h-4 w-4 text-green-600 mx-auto" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            ツール設定
          </DialogTitle>
        </DialogHeader>

        {initialLoading ? (
          <div className="py-8 text-center text-muted-foreground">
            読み込み中...
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {/* モード選択 */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                エージェントのツール許可モードを選択:
              </p>

              <label
                className={`block p-3 border rounded-lg cursor-pointer transition-colors ${
                  mode === 'read_only'
                    ? 'border-primary bg-primary/5'
                    : 'hover:bg-muted/50'
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  value="read_only"
                  checked={mode === 'read_only'}
                  onChange={() => setMode('read_only')}
                  className="sr-only"
                />
                <div className="font-medium">読み取り専用 (デフォルト・推奨)</div>
                <div className="text-sm text-muted-foreground">
                  ファイルの読み取りと検索のみ許可。安全に議論を行えます。
                </div>
              </label>

              <label
                className={`block p-3 border rounded-lg cursor-pointer transition-colors ${
                  mode === 'system_default'
                    ? 'border-primary bg-primary/5'
                    : 'hover:bg-muted/50'
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  value="system_default"
                  checked={mode === 'system_default'}
                  onChange={() => setMode('system_default')}
                  className="sr-only"
                />
                <div className="font-medium">システムデフォルト</div>
                <div className="text-sm text-muted-foreground">
                  すべてのツールを許可。⚠️ ファイル編集・コマンド実行が可能になります。
                </div>
              </label>
            </div>

            {/* ツール許可テーブル */}
            {permissions && (
              <div className="space-y-3">
                <h3 className="font-medium text-sm text-muted-foreground">
                  ツール許可状況
                </h3>

                {renderToolTable(
                  'Claude Code',
                  permissions.claude_code.read_only,
                  permissions.claude_code.system_default
                )}

                {renderToolTable(
                  'Codex',
                  permissions.codex.read_only,
                  permissions.codex.system_default
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t">
          <Button variant="outline" onClick={onClose}>
            キャンセル
          </Button>
          <Button onClick={handleSave} disabled={loading || initialLoading}>
            {loading ? '保存中...' : '保存'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
