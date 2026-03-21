<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouterStore } from '@/stores'
import { ArrowLeft } from 'lucide-vue-next'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import PageHeader from '@/components/PageHeader.vue'
import AppButton from '@/components/AppButton.vue'

const route = useRoute()
const router = useRouter()
const routerStore = useRouterStore()

const terminalRef = ref<HTMLDivElement | null>(null)
const connected = ref(false)
const connecting = ref(false)
const error = ref('')
const routerName = ref('')
const debugLog = ref<string[]>([])

let term: Terminal | null = null
let fitAddonRef: FitAddon | null = null
let ws: WebSocket | null = null

const routerId = Number(route.params.routerId)

const WS_STATES = {
  0: 'CONNECTING',
  1: 'OPEN',
  2: 'CLOSING',
  3: 'CLOSED'
}

function log(msg: string) {
  console.log(msg)
  debugLog.value.push(msg)
}

function initTerminal() {
  log('Initializing terminal...')
  
  if (!terminalRef.value) {
    log('ERROR: Terminal ref is null!')
    error.value = 'Terminal container not found'
    return
  }
  
  log('Creating Terminal instance...')
  
  try {
    term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: '"JetBrains Mono", "Fira Code", Menlo, Monaco, monospace',
      fontSize: 14,
      fontWeight: '400',
      fontWeightBold: '600',
      lineHeight: 1.2,
      theme: {
        background: '#0f172a',
        foreground: '#e2e8f0',
        cursor: '#3b82f6',
        cursorAccent: '#0f172a',
        selection: {
          background: '#3b82f650',
        },
        black: '#1e293b',
        red: '#ef4444',
        green: '#22c55e',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#f1f5f9',
        brightBlack: '#475569',
        brightRed: '#f87171',
        brightGreen: '#4ade80',
        brightYellow: '#fbbf24',
        brightBlue: '#60a5fa',
        brightMagenta: '#c084fc',
        brightCyan: '#22d3ee',
        brightWhite: '#f8fafc',
      },
      allowTransparency: false,
      scrollback: 10000,
      tabStopWidth: 4,
    })

    log('Terminal instance created')

    fitAddonRef = new FitAddon()
    term.loadAddon(fitAddonRef)
    
    log('Opening terminal in DOM...')
    term.open(terminalRef.value)
    
    nextTick(() => {
      if (fitAddonRef) {
        log('Fitting terminal...')
        fitAddonRef.fit()
        log(`Terminal fitted: ${term?.cols}x${term?.rows}`)
      }
    })

    term.onData((data) => {
      log(`onData called: ${JSON.stringify(data)}`)
      if (ws) {
        log(`WebSocket state: ${ws.readyState} (${WS_STATES[ws.readyState] || 'UNKNOWN'})`)
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data)
          log(`Sent data: ${data}`)
        } else {
          log('WebSocket not open, cannot send')
        }
      } else {
        log('WebSocket is null')
      }
    })

    term.onResize(({ cols, rows }) => {
      log(`Terminal resized: ${cols}x${rows}`)
    })

    log('Terminal initialized successfully')
    term.focus()
    log('Terminal focused')
    term.writeln('')
    term.writeln('\x1b[36m╔══════════════════════════════════════════════╗\x1b[0m')
    term.writeln('\x1b[36m║\x1b[1m\x1b[36m      Router MGMT - SSH Terminal\x1b[0m\x1b[36m            ║\x1b[0m')
    term.writeln('\x1b[36m╚══════════════════════════════════════════════╝\x1b[0m')
    term.writeln('')
    
  } catch (err: any) {
    log(`ERROR: ${err.message}`)
    error.value = 'Failed to initialize terminal: ' + err.message
  }
}

function connectWebSocket() {
  if (!term) {
    error.value = 'Terminal not initialized'
    return
  }

  connecting.value = true
  error.value = ''
  term.writeln('\x1b[33m⟳ Connecting to router...\x1b[0m')

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/terminal/${routerId}`
  
  log(`Connecting to WebSocket: ${wsUrl}`)

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      log(`WebSocket connected! ReadyState: ${ws!.readyState} (${WS_STATES[ws!.readyState]})`)
      connected.value = true
      connecting.value = false
    }

    ws.onmessage = (event) => {
      if (term) {
        term.write(event.data)
      }
    }

    ws.onclose = () => {
      log('WebSocket closed')
      connected.value = false
      connecting.value = false
      term?.writeln('')
      term?.writeln('\x1b[33m⟳ Connection closed\x1b[0m')
    }

    ws.onerror = (e) => {
      log('WebSocket error')
      connecting.value = false
      error.value = 'WebSocket connection failed'
      term?.writeln('')
      term?.writeln('\x1b[31m✗ Connection error\x1b[0m')
    }
  } catch (err: any) {
    log(`WebSocket creation error: ${err.message}`)
    connecting.value = false
    error.value = err.message
  }
}

async function initRouter() {
  const r = await routerStore.fetchRouter(routerId)
  if (r) {
    routerName.value = r.hostname
    initTerminal()
    setTimeout(connectWebSocket, 500)
  } else {
    error.value = 'Router not found'
  }
}

function reconnect() {
  if (ws) {
    ws.close()
  }
  if (term) {
    term.clear()
    term.writeln('\x1b[33mReconnecting...\x1b[0m')
  }
  connectWebSocket()
}

function handleResize() {
  if (fitAddonRef) {
    fitAddonRef.fit()
  }
}

onMounted(() => {
  log('Component mounted')
  initRouter()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
  if (term) {
    term.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <div class="h-full flex flex-col">
    <PageHeader :title="routerName || 'Terminal'" :subtitle="`SSH Terminal - Port ${routerId}`">
      <template #actions>
        <div class="flex items-center gap-3">
          <span
            :class="[
              'px-2 py-1 rounded-full text-xs font-medium',
              connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            ]"
          >
            {{ connected ? 'Connected' : (connecting ? 'Connecting...' : 'Disconnected') }}
          </span>
          <AppButton @click="reconnect" variant="ghost" size="sm">
            Reconnect
          </AppButton>
          <AppButton @click="router.push('/terminal')" variant="ghost" size="sm">
            <ArrowLeft class="w-4 h-4" />
            Back
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <div class="flex-1 flex flex-col p-4">
      <div class="flex-1 bg-slate-800 rounded-xl border border-slate-700 overflow-hidden relative">
        <div 
          ref="terminalRef"
          class="w-full h-full"
          style="min-height: 500px; background-color: #0f172a;"
        />
        
        <div v-if="error" class="absolute top-2 right-2 bg-red-500/90 text-white px-3 py-1 rounded text-sm">
          {{ error }}
        </div>
      </div>
      
      <div v-if="debugLog.length > 0" class="mt-2 p-2 bg-slate-900 rounded text-xs font-mono text-slate-400 max-h-24 overflow-auto">
        <div v-for="(msg, i) in debugLog" :key="i">{{ msg }}</div>
      </div>
    </div>
  </div>
</template>

<style>
@import '@xterm/xterm/css/xterm.css';

.xterm {
  height: 100%;
  padding: 12px;
}

.xterm-viewport {
  overflow-y: auto !important;
}

.xterm-viewport::-webkit-scrollbar {
  width: 8px;
}

.xterm-viewport::-webkit-scrollbar-track {
  background: #1e293b;
}

.xterm-viewport::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 4px;
}
</style>
