<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useTemplateStore, useRouterStore } from '@/stores'
import { Plus, Edit2, Trash2, Play, Search, Sparkles, Copy, Route, Globe, Network, Gauge, Shield, RefreshCw, ArrowRight, Lock, Wifi, Key, MoreHorizontal, X, Server, Cable, Send, Terminal, CheckCircle, XCircle, Wand2, Check } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'
import VisualTemplateEditor from '@/components/VisualTemplateEditor.vue'
import type { ConfigTemplate, Vendor, TemplateCategory, AISuggestion } from '@/types'
import { templateApi, PromptGenerateResult, ApplyConfigResult } from '@/api'

const templateStore = useTemplateStore()
const routerStore = useRouterStore()

const searchQuery = ref('')
const selectedVendor = ref('')
const selectedCategory = ref('')
const showAddModal = ref(false)
const showEditModal = ref(false)
const showPreviewModal = ref(false)
const showAISuggestModal = ref(false)
const showPromptModal = ref(false)
const showVisualEditor = ref(false)
const showGeneratedConfig = ref(false)
const generatedConfig = ref('')
const selectedRouterForPushId = ref<number | null>(null)
const selectedRouterForPush = computed(() => 
  routerStore.routers.find(r => r.id === selectedRouterForPushId.value)
)
const editingTemplate = ref<ConfigTemplate | null>(null)
const previewContent = ref('')
const previewVars = ref<Record<string, string>>({})
const loading = ref(false)
const aiLoading = ref(false)
const pushingConfig = ref(false)
const aiSuggestion = ref<AISuggestion | null>(null)

// Apply Template State
const showApplyModal = ref(false)
const applyingTemplate = ref<ConfigTemplate | null>(null)
const applyFormValues = ref<Record<string, any>>({})
const applyRouterId = ref<number | null>(null)
const applyingConfig = ref(false)

// Apply Template Computed
const generatedApplyConfig = computed(() => {
  if (!applyingTemplate.value) return ''
  
  let config = applyingTemplate.value.content
  
  // Replace simple variables
  for (const [key, value] of Object.entries(applyFormValues.value)) {
    const regex = new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, 'g')
    config = config.replace(regex, String(value))
  }
  
  // Handle simple arrays (neighbors, networks) - basic replacement
  // For complex templates, we need more sophisticated parsing
  
  return config
})

function openApplyTemplate(template: ConfigTemplate) {
  applyingTemplate.value = template
  
  // Initialize form values with defaults
  const initialValues: Record<string, any> = {}
  for (const [key, varDef] of Object.entries(template.variables || {})) {
    if (varDef.type === 'array') {
      initialValues[key] = varDef.default || []
    } else {
      initialValues[key] = varDef.default || ''
    }
  }
  applyFormValues.value = initialValues
  applyRouterId.value = null
  showApplyModal.value = true
}

async function handleApplyTemplateConfig() {
  if (!applyingTemplate.value || !applyRouterId.value) return
  
  applyingConfig.value = true
  try {
    const config = generatedApplyConfig.value
    const result = await routerStore.executeCommand(applyRouterId.value, config)
    if (result.success) {
      alert('Configuration applied successfully!')
      showApplyModal.value = false
      applyingTemplate.value = null
    } else {
      alert('Error: ' + result.output)
    }
  } catch (e: any) {
    alert('Error: ' + e.message)
  } finally {
    applyingConfig.value = false
  }
}

function addArrayItem(key: string) {
  const varDef = applyingTemplate.value?.variables?.[key]
  if (varDef?.type === 'array') {
    const props = varDef.properties || {}
    const newItem: Record<string, any> = {}
    for (const [pKey, pDef] of Object.entries(props)) {
      newItem[pKey] = pDef.default || ''
    }
    
    const current = applyFormValues.value[key] || []
    applyFormValues.value[key] = [...current, newItem]
  }
}

function removeArrayItem(key: string, index: number) {
  const current = applyFormValues.value[key] || []
  applyFormValues.value[key] = current.filter((_: any, i: number) => i !== index)
}

const promptForm = ref({
  prompt: '',
  vendor: 'cisco_ios' as Vendor,
  router_id: null as number | null
})
const promptResult = ref<PromptGenerateResult | null>(null)
const promptApplying = ref(false)
const applyResult = ref<ApplyConfigResult | null>(null)

const form = ref({
  name: '',
  description: '',
  category: 'other' as TemplateCategory,
  vendor: 'cisco_ios' as Vendor,
  content: '',
  variables: {} as Record<string, any>
})

// Visual Editor State
interface VariableRow {
  name: string
  type: 'string' | 'number' | 'boolean'
  label: string
  required: boolean
  defaultValue: string
  description: string
  options?: string
}

interface ConfigLine {
  id: number
  text: string
  indent: string
}

const visualForm = ref({
  name: '',
  description: '',
  category: 'bgp' as TemplateCategory,
  vendor: 'frr_linux' as Vendor
})

const configLines = ref<ConfigLine[]>([
  { id: 1, text: 'router bgp {{ as_number }}', indent: '' },
  { id: 2, text: 'bgp router-id {{ router_id }}', indent: '  ' },
  { id: 3, text: '!', indent: '' }
])

const variables = ref<VariableRow[]>([
  { name: 'as_number', type: 'number', label: 'AS Number', required: true, defaultValue: '65001', description: 'Autonomous System Number' },
  { name: 'router_id', type: 'string', label: 'Router ID', required: true, defaultValue: '10.0.0.1', description: 'BGP Router ID' }
])

const generatedContent = computed(() => {
  let content = ''
  for (const line of configLines.value) {
    content += line.indent + line.text + '\n'
  }
  return content
})

const generatedVariables = computed(() => {
  const vars: Record<string, any> = {}
  for (const v of variables.value) {
    vars[v.name] = {
      type: v.type,
      label: v.label,
      required: v.required,
      default: v.defaultValue || undefined,
      description: v.description || undefined,
      ...(v.options ? { options: v.options.split(',').map(o => o.trim()) } : {})
    }
  }
  return vars
})

function addConfigLine() {
  configLines.value.push({
    id: Date.now(),
    text: '',
    indent: '  '
  })
}

function removeConfigLine(id: number) {
  configLines.value = configLines.value.filter(l => l.id !== id)
}

function addVariable() {
  variables.value.push({
    name: '',
    type: 'string',
    label: '',
    required: false,
    defaultValue: '',
    description: ''
  })
}

function removeVariable(index: number) {
  variables.value.splice(index, 1)
}

function saveVisualTemplate() {
  form.value.name = visualForm.value.name
  form.value.description = visualForm.value.description
  form.value.category = visualForm.value.category
  form.value.vendor = visualForm.value.vendor
  form.value.content = generatedContent.value
  form.value.variables = generatedVariables.value
  
  handleAddTemplate()
  showVisualEditor.value = false
  resetVisualForm()
}

function resetVisualForm() {
  visualForm.value = {
    name: '',
    description: '',
    category: 'bgp',
    vendor: 'frr_linux'
  }
  configLines.value = [
    { id: 1, text: 'router bgp {{ as_number }}', indent: '' },
    { id: 2, text: '  bgp router-id {{ router_id }}', indent: '  ' },
    { id: 3, text: '!', indent: '' }
  ]
  variables.value = [
    { name: 'as_number', type: 'number', label: 'AS Number', required: true, defaultValue: '65001', description: 'Autonomous System Number' },
    { name: 'router_id', type: 'string', label: 'Router ID', required: true, defaultValue: '10.0.0.1', description: 'BGP Router ID' }
  ]
}

const aiForm = ref({
  category: 'ospf' as TemplateCategory,
  vendor: 'cisco_ios' as Vendor,
  description: '',
  network_info: ''
})

const vendors = [
  { value: 'cisco_ios', label: 'Cisco IOS' },
  { value: 'cisco_ios_xe', label: 'Cisco IOS-XE' },
  { value: 'juniper_junos', label: 'Juniper JunOS' },
  { value: 'mikrotik_routeros', label: 'MikroTik RouterOS' },
  { value: 'huawei', label: 'Huawei' },
  { value: 'arista_eos', label: 'Arista EOS' },
  { value: 'vyos', label: 'VyOS' },
  { value: 'frr_linux', label: 'FRR Linux' },
  { value: 'generic', label: 'Generic' }
]

const categories = [
  { value: 'ospf', label: 'OSPF', icon: Route },
  { value: 'bgp', label: 'BGP', icon: Globe },
  { value: 'vlan', label: 'VLAN', icon: Network },
  { value: 'interface', label: 'Interface', icon: Server },
  { value: 'qos', label: 'QoS', icon: Gauge },
  { value: 'firewall', label: 'Firewall', icon: Shield },
  { value: 'nat', label: 'NAT', icon: RefreshCw },
  { value: 'routing', label: 'Routing', icon: ArrowRight },
  { value: 'security', label: 'Security', icon: Lock },
  { value: 'wireless', label: 'Wireless', icon: Wifi },
  { value: 'vpn', label: 'VPN', icon: Key },
  { value: 'other', label: 'Other', icon: MoreHorizontal }
]

const categoryOptions = [
  { value: 'ospf', label: 'OSPF' },
  { value: 'bgp', label: 'BGP' },
  { value: 'vlan', label: 'VLAN' },
  { value: 'interface', label: 'Interface' },
  { value: 'qos', label: 'QoS' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'nat', label: 'NAT' },
  { value: 'routing', label: 'Routing' },
  { value: 'security', label: 'Security' },
  { value: 'wireless', label: 'Wireless' },
  { value: 'vpn', label: 'VPN' },
  { value: 'other', label: 'Other' }
]

const filteredTemplates = computed(() => {
  return templateStore.templates.filter(t => {
    const matchesSearch = !searchQuery.value ||
      t.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (t.description && t.description.toLowerCase().includes(searchQuery.value.toLowerCase()))
    const matchesVendor = !selectedVendor.value || t.vendor === selectedVendor.value
    const matchesCategory = !selectedCategory.value || t.category === selectedCategory.value
    return matchesSearch && matchesVendor && matchesCategory
  })
})

function getCategoryIcon(category: string) {
  const cat = categories.find(c => c.value === category)
  return cat?.icon || MoreHorizontal
}

function getCategoryLabel(category: string) {
  const cat = categories.find(c => c.value === category)
  return cat?.label || category
}

async function loadTemplates() {
  await templateStore.fetchTemplates()
}

async function handleAddTemplate() {
  loading.value = true
  try {
    const result = await templateStore.createTemplate(form.value)
    if (result) {
      showAddModal.value = false
      resetForm()
    }
  } finally {
    loading.value = false
  }
}

async function handleVisualSave(data: any) {
  loading.value = true
  try {
    form.value = {
      name: data.name,
      description: data.description,
      category: data.category as TemplateCategory,
      vendor: data.vendor as Vendor,
      content: data.content,
      variables: data.variables
    }
    const result = await templateStore.createTemplate(form.value)
    if (result) {
      showVisualEditor.value = false
      showGeneratedConfig.value = true
      generatedConfig.value = data.content
    }
  } finally {
    loading.value = false
  }
}

async function pushConfigToRouter() {
  if (!selectedRouterForPushId.value) return
  
  pushingConfig.value = true
  try {
    const result = await routerStore.executeCommand(selectedRouterForPushId.value, generatedConfig.value)
    if (result.success) {
      alert('Configuration pushed successfully!')
      showGeneratedConfig.value = false
      selectedRouterForPushId.value = null
    } else {
      alert('Error: ' + result.output)
    }
  } catch (e: any) {
    alert('Error: ' + e.message)
  } finally {
    pushingConfig.value = false
  }
}

async function handleEditTemplate() {
  if (!editingTemplate.value) return
  loading.value = true
  try {
    const result = await templateStore.updateTemplate(editingTemplate.value.id, form.value)
    if (result) {
      showEditModal.value = false
      editingTemplate.value = null
      resetForm()
    }
  } finally {
    loading.value = false
  }
}

function openEdit(template: ConfigTemplate) {
  editingTemplate.value = template
  form.value = {
    name: template.name,
    description: template.description || '',
    category: template.category,
    vendor: template.vendor,
    content: template.content,
    variables: template.variables || {}
  }
  showEditModal.value = true
}

async function handleDelete(template: ConfigTemplate) {
  if (confirm(`Delete template ${template.name}?`)) {
    await templateStore.deleteTemplate(template.id)
  }
}

async function handleAISuggest() {
  aiLoading.value = true
  aiSuggestion.value = null
  try {
    const response = await templateApi.getAiSuggestion({
      category: aiForm.value.category,
      vendor: aiForm.value.vendor,
      description: aiForm.value.description || undefined,
      network_info: aiForm.value.network_info || undefined
    })
    aiSuggestion.value = response.data
  } catch (e: any) {
    alert('AI suggestion failed: ' + e.message)
  } finally {
    aiLoading.value = false
  }
}

function useAISuggestion() {
  if (!aiSuggestion.value) return
  form.value.content = aiSuggestion.value.configuration
  form.value.description = aiSuggestion.value.explanation || aiSuggestion.value.suggestion
  form.value.category = aiForm.value.category
  form.value.vendor = aiForm.value.vendor
  showAISuggestModal.value = false
  showAddModal.value = true
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
}

async function handlePreview() {
  if (!editingTemplate.value && !form.value.content) return
  const templateId = editingTemplate.value?.id
  if (!templateId) {
    previewContent.value = form.value.content
    showPreviewModal.value = true
    return
  }
  
  const vars: Record<string, any> = {}
  Object.entries(previewVars.value).forEach(([k, v]) => {
    if (v) vars[k] = v
  })
  
  try {
    previewContent.value = await templateStore.renderTemplate(templateId, vars)
    showPreviewModal.value = true
  } catch (e: any) {
    alert('Preview failed: ' + e.message)
  }
}

function resetForm() {
  form.value = {
    name: '',
    description: '',
    category: 'other',
    vendor: 'cisco_ios',
    content: '',
    variables: {}
  }
}

async function handlePromptGenerate() {
  if (!promptForm.value.prompt.trim()) {
    alert('Please enter a prompt')
    return
  }
  aiLoading.value = true
  promptResult.value = null
  applyResult.value = null
  try {
    const response = await templateApi.generateFromPrompt({
      prompt: promptForm.value.prompt,
      vendor: promptForm.value.vendor
    })
    promptResult.value = response.data
  } catch (e: any) {
    alert('Failed to generate: ' + e.message)
  } finally {
    aiLoading.value = false
  }
}

async function handleApplyConfig() {
  if (!promptResult.value) return
  if (!promptForm.value.router_id) {
    alert('Please select a router to apply configuration')
    return
  }
  promptApplying.value = true
  applyResult.value = null
  try {
    const response = await templateApi.applyConfig({
      configuration: promptResult.value.configuration,
      router_id: promptForm.value.router_id
    })
    applyResult.value = response.data
  } catch (e: any) {
    applyResult.value = {
      success: false,
      output: '',
      error: e.message
    }
  } finally {
    promptApplying.value = false
  }
}

function resetPromptForm() {
  promptForm.value = {
    prompt: '',
    vendor: 'cisco_ios',
    router_id: null
  }
  promptResult.value = null
  applyResult.value = null
}

onMounted(async () => {
  await loadTemplates()
  await routerStore.fetchRouters()
})
</script>

<template>
  <div>
    <PageHeader title="Configuration Templates" subtitle="Manage configuration templates with AI-powered suggestions">
      <template #actions>
        <div class="flex items-center gap-3">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search templates..."
              class="pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            />
          </div>
          <select
            v-model="selectedVendor"
            class="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm"
          >
            <option value="">All Vendors</option>
            <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
          </select>
          <select
            v-model="selectedCategory"
            class="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm"
          >
            <option value="">All Categories</option>
            <option v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
          <AppButton @click="showAISuggestModal = true" variant="outline">
            <Sparkles class="w-4 h-4" />
            AI Suggest
          </AppButton>
          <AppButton @click="showPromptModal = true" variant="outline">
            <Terminal class="w-4 h-4" />
            AI Prompt
          </AppButton>
          <AppButton @click="showAddModal = true">
            <Plus class="w-4 h-4" />
            New Template
          </AppButton>
          <AppButton @click="showVisualEditor = true" variant="success">
            <Wand2 class="w-4 h-4" />
            Visual Builder
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div
          v-for="template in filteredTemplates"
          :key="template.id"
          class="bg-slate-800 rounded-xl border border-slate-700 p-5 hover:border-slate-600 transition-colors"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-2">
              <component :is="getCategoryIcon(template.category)" class="w-5 h-5 text-cyan-400" />
              <div>
                <h3 class="font-semibold">{{ template.name }}</h3>
                <p class="text-xs text-slate-400 capitalize">{{ getCategoryLabel(template.category) }}</p>
              </div>
            </div>
            <span v-if="template.is_builtin" class="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded">Built-in</span>
          </div>
          <p v-if="template.description" class="text-sm text-slate-400 mb-4 line-clamp-2">
            {{ template.description }}
          </p>
          <div class="flex items-center gap-2 mb-3">
            <span class="px-2 py-0.5 bg-slate-700 text-slate-300 text-xs rounded capitalize">
              {{ template.vendor.replace('_', ' ') }}
            </span>
            <span class="text-xs text-slate-500">
              {{ Object.keys(template.variables || {}).length }} vars
            </span>
          </div>
          <div class="flex items-center justify-between pt-3 border-t border-slate-700">
            <span class="text-xs text-slate-500">
              {{ new Date(template.created_at).toLocaleDateString() }}
            </span>
            <div class="flex items-center gap-1">
              <button
                @click="copyToClipboard(template.content)"
                class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                title="Copy"
              >
                <Copy class="w-4 h-4" />
              </button>
              <AppButton size="sm" variant="success" @click="openApplyTemplate(template)">
                <Send class="w-3 h-3" />
                Apply
              </AppButton>
              <button
                @click="openEdit(template)"
                class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <Edit2 class="w-4 h-4" />
              </button>
              <button
                v-if="!template.is_builtin"
                @click="handleDelete(template)"
                class="p-1.5 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
        <div v-if="filteredTemplates.length === 0" class="col-span-full text-center py-12 text-slate-400">
          <Sparkles class="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No templates found.</p>
          <p class="text-sm mt-1">Create one or use AI to generate suggestions.</p>
        </div>
      </div>
    </div>

    <Modal :open="showAISuggestModal" title="AI Template Suggestion" size="xl" @close="showAISuggestModal = false">
      <div class="space-y-4">
        <div class="flex items-center gap-2 p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
          <Sparkles class="w-5 h-5 text-cyan-400" />
          <p class="text-sm text-cyan-300">Describe what you need and AI will generate a configuration template for you.</p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Category *</label>
            <select v-model="aiForm.category" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg">
              <option v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Vendor *</label>
            <select v-model="aiForm.vendor" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg">
              <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Description (what you need)</label>
          <textarea
            v-model="aiForm.description"
            rows="2"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., OSPF area 0 with network 192.168.1.0/24"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Network Details (optional)</label>
          <textarea
            v-model="aiForm.network_info"
            rows="2"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Router ID 10.0.0.1, interfaces GigabitEthernet0/0"
          />
        </div>
      </div>
      
      <div v-if="aiSuggestion" class="mt-4 space-y-3">
        <div class="p-4 bg-slate-900 rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-cyan-400">Generated Configuration</span>
            <button @click="copyToClipboard(aiSuggestion.configuration)" class="text-xs text-slate-400 hover:text-white">
              <Copy class="w-4 h-4" />
            </button>
          </div>
          <pre class="text-xs font-mono text-slate-300 whitespace-pre-wrap">{{ aiSuggestion.configuration }}</pre>
        </div>
        <p v-if="aiSuggestion.explanation" class="text-sm text-slate-400">{{ aiSuggestion.explanation }}</p>
      </div>
      
      <template #footer>
        <AppButton variant="ghost" @click="showAISuggestModal = false">Close</AppButton>
        <AppButton @click="handleAISuggest" :loading="aiLoading">
          <Sparkles class="w-4 h-4" />
          {{ aiSuggestion ? 'Regenerate' : 'Generate' }}
        </AppButton>
        <AppButton v-if="aiSuggestion" @click="useAISuggestion">
          Use This Template
        </AppButton>
      </template>
    </Modal>

    <Modal :open="showAddModal" title="New Template" size="xl" @close="showAddModal = false; resetForm()">
      <form @submit.prevent="handleAddTemplate" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Category *</label>
            <select
              v-model="form.category"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Vendor *</label>
            <select
              v-model="form.vendor"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Description</label>
            <input
              v-model="form.description"
              type="text"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Template Content *</label>
          <textarea
            v-model="form.content"
            required
            rows="12"
            class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            placeholder="interface {{ interface_name }}
 description {{ description }}
 ip address {{ ip_address }} {{ subnet_mask }}"
          />
          <p class="text-xs text-slate-500 mt-1">Use Jinja2 syntax: {{ variable_name }}</p>
        </div>
      </form>
      <template #footer>
        <AppButton variant="ghost" @click="showAddModal = false">Cancel</AppButton>
        <AppButton :loading="loading" @click="handleAddTemplate">Create Template</AppButton>
      </template>
    </Modal>

    <Modal :open="showEditModal" title="Edit Template" size="xl" @close="showEditModal = false; editingTemplate = null; resetForm()">
      <form @submit.prevent="handleEditTemplate" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Category *</label>
            <select
              v-model="form.category"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Vendor *</label>
            <select
              v-model="form.vendor"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Description</label>
            <input
              v-model="form.description"
              type="text"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Template Content *</label>
          <textarea
            v-model="form.content"
            required
            rows="12"
            class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <p class="text-xs text-slate-500 mt-1">Use Jinja2 syntax: {{ variable_name }}</p>
        </div>
        <AppButton type="button" variant="ghost" size="sm" @click="handlePreview">
          <Play class="w-4 h-4" />
          Preview
        </AppButton>
      </form>
      <template #footer>
        <AppButton variant="ghost" @click="showEditModal = false">Cancel</AppButton>
        <AppButton :loading="loading" @click="handleEditTemplate">Save Changes</AppButton>
      </template>
    </Modal>

    <Modal :open="showPreviewModal" title="Template Preview" size="xl" @close="showPreviewModal = false">
      <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-96">{{ previewContent }}</pre>
    </Modal>

    <Modal :open="showPromptModal" title="AI Configuration Generator" size="xl" @close="showPromptModal = false; resetPromptForm()">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-1">Natural Language Prompt</label>
          <textarea
            v-model="promptForm.prompt"
            rows="4"
            placeholder="e.g., create interface loopback 10 with ip address 10.56.78.1/32"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
          />
          <p class="text-xs text-slate-500 mt-1">
            Describe what you want: interface, loopback, vlan, ospf, bgp, nat, firewall, vpn, route, dhcp, qos, bridge
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Vendor</label>
            <select
              v-model="promptForm.vendor"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Apply to Router (optional)</label>
            <select
              v-model="promptForm.router_id"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option :value="null">Generate only</option>
              <option v-for="r in routerStore.routers" :key="r.id" :value="r.id">
                {{ r.hostname }} ({{ r.ip_address }})
              </option>
            </select>
          </div>
        </div>

        <AppButton :loading="aiLoading" @click="handlePromptGenerate">
          <Sparkles class="w-4 h-4" />
          Generate Configuration
        </AppButton>

        <div v-if="promptResult" class="space-y-4">
          <div class="border-t border-slate-600 pt-4">
            <div class="flex items-center justify-between mb-2">
              <h4 class="font-medium text-cyan-400">Generated Configuration</h4>
              <button
                @click="copyToClipboard(promptResult.configuration)"
                class="text-sm text-slate-400 hover:text-white flex items-center gap-1"
              >
                <Copy class="w-4 h-4" />
                Copy
              </button>
            </div>
            <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-64">{{ promptResult.configuration }}</pre>
          </div>

          <div v-if="promptResult.explanation" class="text-sm text-slate-400">
            <strong>Explanation:</strong> {{ promptResult.explanation }}
          </div>

          <div v-if="promptForm.router_id" class="flex gap-2">
            <AppButton :loading="promptApplying" @click="handleApplyConfig">
              <Terminal class="w-4 h-4" />
              Apply to Router
            </AppButton>
          </div>

          <div v-if="applyResult" class="border-t border-slate-600 pt-4">
            <div class="flex items-center gap-2 mb-2">
              <CheckCircle v-if="applyResult.success" class="w-5 h-5 text-green-400" />
              <XCircle v-else class="w-5 h-5 text-red-400" />
              <h4 :class="['font-medium', applyResult.success ? 'text-green-400' : 'text-red-400']">
                {{ applyResult.success ? 'Configuration Applied Successfully' : 'Configuration Failed' }}
              </h4>
            </div>
            <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-48">{{ applyResult.output }}</pre>
            <p v-if="applyResult.error" class="mt-2 text-sm text-red-400">{{ applyResult.error }}</p>
          </div>
        </div>
      </div>
      <template #footer>
        <AppButton variant="ghost" @click="showPromptModal = false; resetPromptForm()">Close</AppButton>
      </template>
    </Modal>

    <!-- Visual Template Editor Modal -->
    <VisualTemplateEditor 
      :open="showVisualEditor" 
      @close="showVisualEditor = false"
      @save="handleVisualSave"
    />

    <!-- Generated Config Preview & Push Modal -->
    <Modal :open="showGeneratedConfig" title="Generated Configuration" size="xl" @close="showGeneratedConfig = false">
      <div class="space-y-4">
        <div class="bg-slate-900 p-4 rounded-lg">
          <pre class="text-xs font-mono whitespace-pre-wrap text-green-400">{{ generatedConfig }}</pre>
        </div>
        
        <div v-if="selectedRouterForPush" class="p-4 bg-slate-700 rounded-lg">
          <p class="text-sm text-slate-300 mb-2">
            Ready to push to: <span class="font-bold text-white">{{ selectedRouterForPush.hostname }}</span>
            ({{ selectedRouterForPush.ip_address }})
          </p>
          <p class="text-xs text-slate-400">Vendor: {{ selectedRouterForPush.vendor }}</p>
        </div>
        
        <div>
          <label class="block text-sm font-medium mb-2">Select Router to Push</label>
          <select 
            v-model="selectedRouterForPushId"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          >
            <option :value="null">-- Select a router --</option>
            <option v-for="r in routerStore.routers" :key="r.id" :value="r.id">
              {{ r.hostname }} ({{ r.ip_address }})
            </option>
          </select>
        </div>
      </div>
      
      <template #footer>
        <AppButton variant="ghost" @click="showGeneratedConfig = false">Cancel</AppButton>
        <AppButton 
          variant="success" 
          :loading="pushingConfig" 
          :disabled="!selectedRouterForPushId"
          @click="pushConfigToRouter"
        >
          <Send class="w-4 h-4" />
          Push to Router
        </AppButton>
      </template>
    </Modal>

    <!-- Apply Template Modal -->
    <Modal :open="showApplyModal" :title="`Apply Template: ${applyingTemplate?.name || ''}`" size="xl" @close="showApplyModal = false; applyingTemplate = null">
      <div v-if="applyingTemplate" class="space-y-6">
        <!-- Template Info -->
        <div class="bg-slate-700/50 p-3 rounded-lg">
          <p class="text-sm text-slate-300">
            <span class="font-medium">Vendor:</span> {{ applyingTemplate.vendor }} | 
            <span class="font-medium">Category:</span> {{ applyingTemplate.category }}
          </p>
        </div>

        <!-- Variable Form -->
        <div class="space-y-4">
          <h3 class="font-medium text-cyan-400">Fill Variables</h3>
          
          <template v-for="(varDef, key) in applyingTemplate.variables" :key="key">
            <!-- String/Number Input -->
            <div v-if="varDef.type === 'string' || varDef.type === 'number'">
              <label class="block text-sm font-medium mb-1">
                {{ varDef.label || key }} 
                <span v-if="varDef.required" class="text-red-400">*</span>
              </label>
              <input
                v-model="applyFormValues[key]"
                :type="varDef.type === 'number' ? 'number' : 'text'"
                :placeholder="varDef.description || ''"
                class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <!-- Select Input -->
            <div v-else-if="varDef.type === 'select' || varDef.options">
              <label class="block text-sm font-medium mb-1">
                {{ varDef.label || key }}
                <span v-if="varDef.required" class="text-red-400">*</span>
              </label>
              <select
                v-model="applyFormValues[key]"
                class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option v-for="opt in (varDef.options || [])" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </div>

            <!-- Array Input -->
            <div v-else-if="varDef.type === 'array'">
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm font-medium">
                  {{ varDef.label || key }}
                  <span v-if="varDef.required" class="text-red-400">*</span>
                </label>
                <AppButton size="sm" variant="outline" @click="addArrayItem(key)">
                  <Plus class="w-3 h-3" />
                  Add
                </AppButton>
              </div>
              
              <!-- Array Items -->
              <div v-for="(item, index) in (applyFormValues[key] || [])" :key="index" class="bg-slate-700/50 p-3 rounded-lg mb-2">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs text-slate-400">Item {{ index + 1 }}</span>
                  <button @click="removeArrayItem(key, index)" class="text-red-400 hover:text-red-300">
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <template v-for="(propDef, propKey) in varDef.properties" :key="propKey">
                    <div>
                      <label class="block text-xs text-slate-400 mb-1">{{ propDef.label || propKey }}</label>
                      <input
                        v-model="item[propKey]"
                        type="text"
                        :placeholder="propDef.label || ''"
                        class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Preview Generated Config -->
        <div>
          <h3 class="font-medium text-cyan-400 mb-2">Generated Configuration</h3>
          <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap text-green-400">{{ generatedApplyConfig }}</pre>
        </div>

        <!-- Select Router -->
        <div>
          <label class="block text-sm font-medium mb-2">Select Router to Apply</label>
          <select 
            v-model="applyRouterId"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option :value="null">-- Select a router --</option>
            <option 
              v-for="r in routerStore.routers.filter(r => r.vendor === applyingTemplate.vendor)" 
              :key="r.id" 
              :value="r.id"
            >
              {{ r.hostname }} ({{ r.ip_address }})
            </option>
          </select>
          <p v-if="!routerStore.routers.filter(r => r.vendor === applyingTemplate.vendor).length" class="text-xs text-amber-400 mt-1">
            No routers found with vendor: {{ applyingTemplate.vendor }}
          </p>
        </div>
      </div>

      <template #footer>
        <AppButton variant="ghost" @click="showApplyModal = false">Cancel</AppButton>
        <AppButton 
          variant="success" 
          :loading="applyingConfig" 
          :disabled="!applyRouterId"
          @click="handleApplyTemplateConfig"
        >
          <Send class="w-4 h-4" />
          Apply Configuration
        </AppButton>
      </template>
    </Modal>
  </div>
</template>
