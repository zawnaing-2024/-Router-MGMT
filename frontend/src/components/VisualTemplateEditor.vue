<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, Trash2, Save, Eye, X, ChevronDown, ChevronUp } from 'lucide-vue-next'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [data: { name: string, description: string, category: string, vendor: string, content: string, variables: Record<string, any> }]
}>()

// Template basic info
const templateInfo = ref({
  name: '',
  description: '',
  category: 'bgp',
  vendor: 'frr_linux'
})

// Config sections
interface ConfigSection {
  id: number
  name: string
  lines: ConfigLine[]
  collapsed: boolean
}

interface ConfigLine {
  id: number
  text: string
}

// Variable definitions
interface VariableDef {
  id: number
  name: string
  type: 'string' | 'number' | 'boolean' | 'select'
  label: string
  required: boolean
  defaultValue: string
  description: string
  options?: string
}

const configSections = ref<ConfigSection[]>([
  {
    id: 1,
    name: 'Basic Configuration',
    collapsed: false,
    lines: [
      { id: 1, text: 'router bgp {{ as_number }}' },
      { id: 2, text: ' bgp router-id {{ router_id }}' }
    ]
  }
])

const variables = ref<VariableDef[]>([
  { id: 1, name: 'as_number', type: 'number', label: 'AS Number', required: true, defaultValue: '65001', description: 'Autonomous System Number' },
  { id: 2, name: 'router_id', type: 'string', label: 'Router ID', required: true, defaultValue: '10.0.0.1', description: 'BGP Router ID (loopback IP)' }
])

// Template presets
const templatePresets = [
  { 
    id: 'bgp', 
    name: 'BGP Configuration',
    sections: [
      { name: 'Basic', lines: ['router bgp {{ as_number }}', ' bgp router-id {{ router_id }}'] },
      { name: 'Neighbor', lines: ['neighbor {{ neighbor_ip }} remote-as {{ neighbor_as }}', 'neighbor {{ neighbor_ip }} description {{ neighbor_desc }}', 'neighbor {{ neighbor_ip }} password {{ neighbor_password }}', 'neighbor {{ neighbor_ip }} activate'] },
      { name: 'Address Family', lines: ['address-family ipv4 unicast', ' redistribute connected', 'exit-address-family'] }
    ],
    variables: [
      { name: 'as_number', type: 'number', label: 'AS Number' },
      { name: 'router_id', type: 'string', label: 'Router ID' },
      { name: 'neighbor_ip', type: 'string', label: 'Neighbor IP' },
      { name: 'neighbor_as', type: 'number', label: 'Remote AS' },
      { name: 'neighbor_desc', type: 'string', label: 'Neighbor Description' },
      { name: 'neighbor_password', type: 'string', label: 'Password (optional)' }
    ]
  },
  { 
    id: 'ospf', 
    name: 'OSPF Configuration',
    sections: [
      { name: 'OSPF Basic', lines: ['router ospf {{ process_id }}', ' ospf router-id {{ router_id }}', ' redistribute connected'] },
      { name: 'Network', lines: ['network {{ network }} area {{ area }}'] }
    ],
    variables: [
      { name: 'process_id', type: 'number', label: 'Process ID' },
      { name: 'router_id', type: 'string', label: 'Router ID' },
      { name: 'network', type: 'string', label: 'Network (e.g., 10.0.0.0/24)' },
      { name: 'area', type: 'number', label: 'OSPF Area' }
    ]
  },
  { 
    id: 'interface', 
    name: 'Interface Configuration',
    sections: [
      { name: 'Interface', lines: ['interface {{ interface_name }}', ' description {{ description }}', ' ip address {{ ip_address }}/{{ subnet }}', ' no shutdown'] }
    ],
    variables: [
      { name: 'interface_name', type: 'string', label: 'Interface Name' },
      { name: 'description', type: 'string', label: 'Description' },
      { name: 'ip_address', type: 'string', label: 'IP Address' },
      { name: 'subnet', type: 'number', label: 'Subnet (CIDR)' }
    ]
  },
  { 
    id: 'static_route', 
    name: 'Static Route',
    sections: [
      { name: 'Static Route', lines: ['ip route {{ destination }}/{{ prefix }} {{ next_hop }}'] }
    ],
    variables: [
      { name: 'destination', type: 'string', label: 'Destination Network' },
      { name: 'prefix', type: 'number', label: 'Prefix Length' },
      { name: 'next_hop', type: 'string', label: 'Next Hop IP' }
    ]
  },
  { 
    id: 'vlan', 
    name: 'VLAN Configuration',
    sections: [
      { name: 'VLAN', lines: ['vlan {{ vlan_id }}', ' name {{ vlan_name }}'], },
      { name: 'Interface', lines: ['interface {{ interface }}', ' switchport mode access', ' switchport access vlan {{ vlan_id }}'] }
    ],
    variables: [
      { name: 'vlan_id', type: 'number', label: 'VLAN ID' },
      { name: 'vlan_name', type: 'string', label: 'VLAN Name' },
      { name: 'interface', type: 'string', label: 'Interface Name' }
    ]
  },
  { 
    id: 'custom', 
    name: 'Custom Template',
    sections: [],
    variables: []
  }
]

const selectedPreset = ref('custom')

function loadPreset(presetId: string) {
  const preset = templatePresets.find(p => p.id === presetId)
  if (!preset || presetId === 'custom') {
    selectedPreset.value = 'custom'
    return
  }
  
  selectedPreset.value = presetId
  templateInfo.value.category = presetId === 'bgp' ? 'bgp' : presetId === 'ospf' ? 'ospf' : 'other'
  
  // Load sections
  configSections.value = preset.sections.map((s, idx) => ({
    id: idx + 1,
    name: s.name,
    collapsed: false,
    lines: s.lines.map((l, lineIdx) => ({ id: lineIdx + 1, text: l }))
  }))
  
  // Load variables
  variables.value = preset.variables.map((v, idx) => ({
    id: idx + 1,
    name: v.name,
    type: v.type as any,
    label: v.label,
    required: true,
    defaultValue: '',
    description: ''
  }))
}

function addSection() {
  configSections.value.push({
    id: Date.now(),
    name: 'New Section',
    collapsed: false,
    lines: []
  })
}

function removeSection(sectionId: number) {
  configSections.value = configSections.value.filter(s => s.id !== sectionId)
}

function toggleSection(sectionId: number) {
  const section = configSections.value.find(s => s.id === sectionId)
  if (section) {
    section.collapsed = !section.collapsed
  }
}

function addLine(sectionId: number) {
  const section = configSections.value.find(s => s.id === sectionId)
  if (section) {
    section.lines.push({ id: Date.now(), text: '' })
  }
}

function removeLine(sectionId: number, lineId: number) {
  const section = configSections.value.find(s => s.id === sectionId)
  if (section) {
    section.lines = section.lines.filter(l => l.id !== lineId)
  }
}

function addVariable() {
  variables.value.push({
    id: Date.now(),
    name: '',
    type: 'string',
    label: '',
    required: false,
    defaultValue: '',
    description: ''
  })
}

function removeVariable(varId: number) {
  variables.value = variables.value.filter(v => v.id !== varId)
}

// Generate content
const generatedContent = computed(() => {
  let content = ''
  for (const section of configSections.value) {
    for (const line of section.lines) {
      if (line.text.trim()) {
        content += line.text + '\n'
      }
    }
    content += '!\n'
  }
  return content
})

// Generate variables
const generatedVariables = computed(() => {
  const vars: Record<string, any> = {}
  for (const v of variables.value) {
    if (!v.name) continue
    vars[v.name] = {
      type: v.type,
      label: v.label || v.name,
      required: v.required,
      default: v.defaultValue || undefined,
      description: v.description || undefined,
      ...(v.options ? { options: v.options.split(',').map(o => o.trim()) } : {})
    }
  }
  return vars
})

// Preview state
const showPreview = ref(false)

function preview() {
  showPreview.value = true
}

function save() {
  if (!templateInfo.value.name) {
    alert('Please enter a template name')
    return
  }
  
  emit('save', {
    name: templateInfo.value.name,
    description: templateInfo.value.description,
    category: templateInfo.value.category,
    vendor: templateInfo.value.vendor,
    content: generatedContent.value,
    variables: generatedVariables.value
  })
}
</script>

<template>
  <Modal :open="open" title="Create Custom Template" size="xl" @close="emit('close')">
    <div class="space-y-6 max-h-[70vh] overflow-y-auto pr-2">
      <!-- Presets -->
      <div>
        <label class="block text-sm font-medium mb-2">Start from Preset (optional)</label>
        <select 
          v-model="selectedPreset" 
          @change="loadPreset(selectedPreset)"
          class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg"
        >
          <option v-for="preset in templatePresets" :key="preset.id" :value="preset.id">
            {{ preset.name }}
          </option>
        </select>
      </div>

      <!-- Basic Info -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Template Name *</label>
          <input
            v-model="templateInfo.name"
            type="text"
            placeholder="e.g., My BGP Template"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Vendor</label>
          <select v-model="templateInfo.vendor" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg">
            <option value="frr_linux">FRR Linux</option>
            <option value="cisco_ios">Cisco IOS</option>
            <option value="cisco_ios_xe">Cisco IOS-XE</option>
            <option value="juniper_junos">Juniper JunOS</option>
            <option value="mikrotik_routeros">MikroTik RouterOS</option>
            <option value="huawei">Huawei</option>
            <option value="arista_eos">Arista EOS</option>
            <option value="vyos">VyOS</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Category</label>
          <select v-model="templateInfo.category" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg">
            <option value="bgp">BGP</option>
            <option value="ospf">OSPF</option>
            <option value="interface">Interface</option>
            <option value="routing">Routing</option>
            <option value="vlan">VLAN</option>
            <option value="firewall">Firewall</option>
            <option value="nat">NAT</option>
            <option value="vpn">VPN</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Description</label>
          <input
            v-model="templateInfo.description"
            type="text"
            placeholder="Brief description"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          />
        </div>
      </div>

      <!-- Config Lines -->
      <div class="border-t border-slate-600 pt-4">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-medium text-cyan-400">Configuration Lines</h3>
          <AppButton size="sm" @click="addSection">
            <Plus class="w-4 h-4" />
            Add Section
          </AppButton>
        </div>

        <div v-for="section in configSections" :key="section.id" class="mb-4 bg-slate-700/50 rounded-lg overflow-hidden">
          <div 
            class="flex items-center justify-between p-3 bg-slate-700 cursor-pointer"
            @click="toggleSection(section.id)"
          >
            <span class="font-medium">{{ section.name }}</span>
            <div class="flex items-center gap-2">
              <button @click.stop="addLine(section.id)" class="p-1 hover:bg-slate-600 rounded">
                <Plus class="w-4 h-4" />
              </button>
              <button @click.stop="removeSection(section.id)" class="p-1 hover:bg-red-500/30 rounded text-red-400">
                <Trash2 class="w-4 h-4" />
              </button>
              <component :is="section.collapsed ? ChevronDown : ChevronUp" class="w-4 h-4" />
            </div>
          </div>
          
          <div v-if="!section.collapsed" class="p-3 space-y-2">
            <div v-for="line in section.lines" :key="line.id" class="flex items-center gap-2">
              <input
                v-model="line.text"
                type="text"
                placeholder="e.g., router bgp {{ as_number }}"
                class="flex-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded text-sm font-mono"
              />
              <button @click="removeLine(section.id, line.id)" class="p-1 hover:bg-red-500/30 rounded text-red-400">
                <X class="w-4 h-4" />
              </button>
            </div>
            <p class="text-xs text-slate-400">
              Use <code class="bg-slate-800 px-1 rounded">{'{{ variable_name }}'}</code> for variables
            </p>
          </div>
        </div>

        <p v-if="configSections.length === 0" class="text-center text-slate-400 py-4">
          No sections yet. Click "Add Section" to start.
        </p>
      </div>

      <!-- Variables -->
      <div class="border-t border-slate-600 pt-4">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-medium text-cyan-400">Variables</h3>
          <AppButton size="sm" variant="outline" @click="addVariable">
            <Plus class="w-4 h-4" />
            Add Variable
          </AppButton>
        </div>

        <div class="space-y-3">
          <div v-for="variable in variables" :key="variable.id" class="bg-slate-700/50 p-3 rounded-lg">
            <div class="grid grid-cols-4 gap-3">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Name *</label>
                <input
                  v-model="variable.name"
                  type="text"
                  placeholder="variable_name"
                  class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm"
                />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Type</label>
                <select v-model="variable.type" class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm">
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="boolean">Boolean</option>
                  <option value="select">Select</option>
                </select>
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Label</label>
                <input
                  v-model="variable.label"
                  type="text"
                  placeholder="Display Label"
                  class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm"
                />
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Default</label>
                <input
                  v-model="variable.defaultValue"
                  type="text"
                  placeholder="Default value"
                  class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm"
                />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-2">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Options (for Select type)</label>
                <input
                  v-model="variable.options"
                  type="text"
                  placeholder="option1, option2, option3"
                  class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm"
                />
              </div>
              <div class="flex items-center gap-2 pt-5">
                <label class="flex items-center gap-1 text-sm">
                  <input type="checkbox" v-model="variable.required" class="w-4 h-4 rounded" />
                  Required
                </label>
                <button @click="removeVariable(variable.id)" class="ml-auto p-1 hover:bg-red-500/30 rounded text-red-400">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <p v-if="variables.length === 0" class="text-center text-slate-400 py-4">
          No variables yet. Click "Add Variable" to define template variables.
        </p>
      </div>

      <!-- Preview -->
      <div class="border-t border-slate-600 pt-4">
        <AppButton variant="outline" @click="preview">
          <Eye class="w-4 h-4" />
          Preview Template
        </AppButton>
      </div>
    </div>

    <template #footer>
      <AppButton variant="ghost" @click="emit('close')">Cancel</AppButton>
      <AppButton @click="save">
        <Save class="w-4 h-4" />
        Create Template
      </AppButton>
    </template>
  </Modal>

  <!-- Preview Modal -->
  <Modal :open="showPreview" title="Template Preview" size="xl" @close="showPreview = false">
    <div class="space-y-4">
      <div>
        <h4 class="text-sm font-medium text-slate-400 mb-2">Generated Configuration:</h4>
        <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-48 whitespace-pre text-green-400">{{ generatedContent }}</pre>
      </div>
      <div>
        <h4 class="text-sm font-medium text-slate-400 mb-2">Variables:</h4>
        <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-48">{{ JSON.stringify(generatedVariables, null, 2) }}</pre>
      </div>
    </div>
  </Modal>
</template>
