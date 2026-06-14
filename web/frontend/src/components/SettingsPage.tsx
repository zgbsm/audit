import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, CheckCircle, XCircle, AlertTriangle, Key, Server, Info } from 'lucide-react';
import { authCheck } from '@/api/client';
import type { AuthCheckResponse } from '@/api/types';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Spinner } from '@/components/shared/Spinner';

export function SettingsPage() {
  const [allowApiKey, setAllowApiKey] = useState(false);
  const { data: auth, isLoading, error, refetch } = useQuery<AuthCheckResponse>({
    queryKey: ['auth-check', allowApiKey],
    queryFn: () => authCheck(allowApiKey),
  });

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Authentication and configuration</p>
      </div>

      {/* Auth status */}
      <div className="glass-panel p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Key className="h-4 w-4 text-blue-400" />
            Authentication
          </h2>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={allowApiKey}
              onChange={(e) => {
                setAllowApiKey(e.target.checked);
                setTimeout(() => refetch(), 0);
              }}
              className="rounded border-slate-600 bg-slate-800"
            />
            Allow API Key
          </label>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <XCircle className="h-4 w-4" />
            {(error as Error).message}
          </div>
        ) : auth ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {auth.ok ? (
                <CheckCircle className="h-5 w-5 text-green-400" />
              ) : (
                <XCircle className="h-5 w-5 text-red-400" />
              )}
              <span className="text-sm font-medium text-slate-200">
                {auth.ok ? 'Authenticated' : 'Not Authenticated'}
              </span>
              {auth.auth_mode && (
                <span className="badge bg-blue-500/20 text-blue-400">{auth.auth_mode}</span>
              )}
            </div>

            {auth.error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
                {auth.error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 text-xs">
              {auth.claude_cli_path && (
                <div className="flex items-center gap-2 text-slate-400">
                  <Server className="h-3.5 w-3.5" />
                  CLI: {auth.claude_cli_path}
                </div>
              )}
              {auth.claude_cli_version && (
                <div className="text-slate-400">Version: {auth.claude_cli_version}</div>
              )}
              {auth.gateway_base_url && (
                <div className="flex items-center gap-2 text-slate-400 col-span-2">
                  <Info className="h-3.5 w-3.5" />
                  Gateway: {auth.gateway_base_url}
                </div>
              )}
              {auth.gateway_model && (
                <div className="text-slate-400 col-span-2">Model: {auth.gateway_model}</div>
              )}
            </div>

            {(auth.api_key_scrubbed || auth.auth_token_scrubbed) && (
              <div className="flex items-center gap-2 text-xs text-yellow-400">
                <AlertTriangle className="h-3.5 w-3.5" />
                {auth.api_key_scrubbed && 'API key scrubbed. '}
                {auth.auth_token_scrubbed && 'Auth token scrubbed.'}
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Config info */}
      <div className="glass-panel p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <Info className="h-4 w-4 text-blue-400" />
          About
        </h2>
        <div className="text-sm text-slate-400 space-y-1">
          <p>Audit Web v0.1.0</p>
          <p>Cloudflare-style 8-stage vulnerability discovery agent</p>
          <p className="text-xs text-slate-600 mt-2">
            Runs on the same machine as the CLI. All pipeline execution happens
            locally using your Claude subscription.
          </p>
        </div>
      </div>
    </div>
  );
}
