import { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '@/api/ws';
import { Brain, Wrench, FileOutput, MessageSquare, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import type { WsEvent } from '@/api/types';

interface StreamMessage {
  kind: string;
  model?: string;
  content?: StreamBlock[];
  data?: {
    num_turns?: number;
    total_cost_usd?: number;
    [key: string]: unknown;
  };
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  is_error?: boolean;
  [key: string]: unknown;
}

interface StreamBlock {
  type: 'thinking' | 'tool_use' | 'tool_result' | 'text';
  thinking?: string;
  text?: string;
  name?: string;
  id?: string;
  input?: Record<string, unknown>;
  tool_use_id?: string;
  content?: string;
  is_error?: boolean;
}

interface Props {
  runId: string;
  className?: string;
}

export function StreamViewer({ runId, className }: Props) {
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [paused, setPaused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useWebSocket({
    runId,
    onMessage: (event: WsEvent) => {
      if (event.type === 'stream_message') {
        const data = event.data as StreamMessage;
        if (!paused) {
          setMessages((prev) => [...prev.slice(-4), data]); // keep latest 5
        }
      }
    },
  });

  // Auto-scroll
  useEffect(() => {
    if (!paused && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, paused]);

  if (messages.length === 0) {
    return (
      <div className={`glass-panel p-4 ${className ?? ''}`}>
        <h3 className="text-sm font-medium text-slate-300 mb-2">AI Stream</h3>
        <p className="text-sm text-slate-600 text-center py-4">
          No messages yet — stream will appear when the pipeline starts
        </p>
      </div>
    );
  }

  return (
    <div className={`glass-panel flex flex-col ${className ?? ''}`}>
      <div className="p-3 border-b border-slate-700/50 flex items-center justify-between flex-shrink-0">
        <h3 className="text-sm font-medium text-slate-300">AI Stream</h3>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>latest {Math.min(messages.length, 5)} message(s)</span>
          <button
            className={`px-2 py-1 rounded ${
              paused ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-800 text-slate-400'
            }`}
            onClick={() => setPaused(!paused)}
          >
            {paused ? 'Paused' : 'Live'}
          </button>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[400px]">
        {messages.map((msg, i) => (
          <StreamMessageView key={i} msg={msg} />
        ))}
      </div>
    </div>
  );
}

function StreamMessageView({ msg }: { msg: StreamMessage }) {
  const [expanded, setExpanded] = useState(true);

  if (msg.kind === 'assistant') {
    return (
      <div className="rounded-lg bg-slate-800/50 border border-slate-700/50 overflow-hidden">
        <div
          className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-800/70"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronDown className="h-3 w-3 text-slate-500" /> : <ChevronRight className="h-3 w-3 text-slate-500" />}
          <Brain className="h-3.5 w-3.5 text-blue-400" />
          <span className="text-xs font-medium text-blue-400">{msg.model || 'AI'}</span>
        </div>
        {expanded && msg.content && (
          <div className="px-3 pb-3 space-y-2">
            {msg.content.map((block, i) => {
              if (block.type === 'thinking') {
                return <ThinkingBlockView key={i} text={block.thinking || ''} />;
              }
              if (block.type === 'tool_use') {
                return <ToolUseBlockView key={i} block={block} />;
              }
              if (block.type === 'tool_result') {
                return <ToolResultBlockView key={i} block={block} />;
              }
              if (block.type === 'text') {
                return (
                  <div key={i} className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {block.text}
                  </div>
                );
              }
              return null;
            })}
          </div>
        )}
      </div>
    );
  }

  if (msg.kind === 'result') {
    return (
      <div className="flex items-center gap-2 px-2 py-1 text-xs">
        <FileOutput className="h-3 w-3 text-green-400" />
        <span className="text-green-400">Done</span>
        <span className="text-slate-500">
          turns={msg.data?.num_turns ?? '?'} cost=${msg.data?.total_cost_usd != null ? Number(msg.data.total_cost_usd).toFixed(4) : '?'}
        </span>
      </div>
    );
  }

  return null;
}

function ThinkingBlockView({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <button
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-400"
        onClick={() => setShow(!show)}
      >
        {show ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Brain className="h-3 w-3" />
        Thinking...
      </button>
      {show && (
        <pre className="mt-1 p-2 rounded bg-slate-950 text-xs text-slate-500 whitespace-pre-wrap max-h-40 overflow-y-auto">
          {text.slice(0, 3000)}
        </pre>
      )}
    </div>
  );
}

function ToolUseBlockView({ block }: { block: StreamBlock }) {
  return (
    <div className="rounded bg-slate-900 border border-slate-700 p-2">
      <div className="flex items-center gap-1.5 text-xs text-cyan-400 mb-1">
        <Wrench className="h-3 w-3" />
        {block.name}
      </div>
      {block.input && (
        <pre className="text-[11px] text-slate-500 whitespace-pre-wrap max-h-32 overflow-y-auto">
          {JSON.stringify(block.input, null, 2).slice(0, 2000)}
        </pre>
      )}
    </div>
  );
}

function ToolResultBlockView({ block }: { block: StreamBlock }) {
  return (
    <div className="rounded bg-slate-900 border border-slate-700 p-2">
      <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
        <FileOutput className="h-3 w-3" />
        Result {block.is_error && <AlertTriangle className="h-3 w-3 text-red-400" />}
      </div>
      {block.content && (
        <pre className="text-[11px] text-slate-500 whitespace-pre-wrap max-h-32 overflow-y-auto">
          {String(block.content).slice(0, 2000)}
        </pre>
      )}
    </div>
  );
}
