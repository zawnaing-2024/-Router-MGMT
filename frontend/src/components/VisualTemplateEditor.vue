<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, Trash2, Save, ArrowLeft, Eye } from 'lucide-vue-next'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [data: { name: string, description: string, category: string, vendor: string, content: string, variables: Record<string, any> }]
}>()

interface Field {
  id: number
  label: string
  type: 'text' | 'number' | 'select' | 'checkbox'
  required: boolean
  defaultValue: string
  options?: string
  placeholder?: string
  help?: string
}

interface TemplateSection {
  id: number
  title: string
  enabled: boolean
  commandTemplate: string
  fields: Field[]
}

const form = ref({
  name: '',
  description: '',
  category: 'bgp',
  vendor: 'frr_linux'
})

const sections = ref<TemplateSection[]>([
  {
    id: 1,
    title: 'BGP Basic',
    enabled: true,
    commandTemplate: 'router bgp {{ as_number }}',
    fields: [
      { id: 1, label: 'AS Number', type: 'number', required: true, defaultValue: '65001', placeholder: '65001', help: 'Your Autonomous System Number' },
      { id: 2, label: 'Router ID', type: 'text', required: true, defaultValue: '10.0.0.1', placeholder: '10.0.0.1', help: 'BGP Router ID (usually loopback IP)' }
    ]
  },
  {
    id: 2,
    title: 'BGP Neighbor',
    enabled: true,
    commandTemplate: `{% for neighbor in neighbors %}
  neighbor {{ neighbor.ip }} remote-as {{ neighbor.as }}
  {% if neighbor.password %}
  neighbor {{ neighbor.ip }} password {{ neighbor.password }}
  {% endif %}
  {% if neighbor.route_map_in %}
  neighbor {{ neighbor.ip }} route-map {{ neighbor.route_map_in }} in
  {% endif %}
  {% if neighbor.route_map_out %}
  neighbor {{ neighbor.ip }} route-map {{ neighbor.route_map_out }} out
  {% endif %}
  neighbor {{ neighbor.ip }} activate
{% endfor %}`,
    fields: []
  },
  {
    id: 3,
    title: 'Address Family',
    enabled: true,
    commandTemplate: `{% if af_type == 'ipv4' or af_type == 'both' %}
  address-family ipv4 unicast
  {% for network in networks %}
    network {{ network }}
  {% endfor %}
  exit-address-family
{% endif %}
{% if af_type == 'ipv6' or af_type == 'both' %}
  address-family ipv6 unicast
  {% for network in networks_ipv6 %}
    network {{ network }}
  {% endfor %}
  exit-address-family
{% endif %}`,
    fields: []
  }
])

const generatedContent = computed(() => {
  let content = ''
  for (const section of sections.value) {
    if (section.enabled) {
      content += section.commandTemplate + '\n'
    }
  }
  return content
})

const generatedVariables = computed(() => {
  const vars: Record<string, any> = {}
  
  for (const section of sections.value) {
    if (!section.enabled) continue
    
    for (const field of section.fields) {
      if (field.type === 'text' || field.type === 'number') {
        vars[field.label.toLowerCase().replace(/\s+/g, '_')] = {
          type: field.type,
          label: field.label,
          required: field.required,
          default: field.defaultValue || undefined,
          description: field.help || undefined
        }
      } else if (field.type === 'select' && field.options) {
        vars[field.label.toLowerCase().replace(/\s+/g, '_')] = {
          type: 'string',
          label: field.label,
          required: field.required,
          default: field.defaultValue || field.options.split(',')[0]?.trim(),
          options: field.options.split(',').map(o => o.trim()),
          description: field.help || undefined
        }
      }
    }
  }
  
  // Always add arrays for neighbors
  vars.neighbors = {
    type: 'array',
    label: 'BGP Neighbors',
    required: false,
    properties: {
      ip: { type: 'string', label: 'Neighbor IP' },
      as: { type: 'number', label: 'Remote AS' },
      password: { type: 'string', label: 'Password (optional)' },
      route_map_in: { type: 'string', label: 'Route-Map In (optional)' },
      route_map_out: { type: 'string', label: 'Route-Map Out (optional)' }
    }
  }
  
  vars.networks = {
    type: 'array',
    label: 'IPv4 Networks',
    required: false,
    properties: {
      prefix: { type: 'string', label: 'Network (e.g. 10.0.0.0/24)' }
    }
  }
  
  vars.networks_ipv6 = {
    type: 'array',
    label: 'IPv6 Networks',
    required: false,
    properties: {
      prefix: { type: 'string', label: 'Network (e.g. 2001:db8::/32)' }
    }
  }
  
  vars.af_type = {
    type: 'string',
    label: 'Address Family',
    options: ['ipv4', 'ipv6', 'both'],
    default: 'ipv4',
    description: 'Select address family type'
  }
  
  return vars
})

const previewContent = ref('')
const showPreview = ref(false)

function preview() {
  previewContent.value = generatedContent.value
  showPreview.value = true
}

function save() {
  if (!form.value.name) {
    alert('Please enter a template name')
    return
  }
  
  emit('save', {
    name: form.value.name,
    description: form.value.description,
    category: form.value.category,
    vendor: form.value.vendor,
    content: generatedContent.value,
    variables: generatedVariables.value
  })
  
  // Reset form
  form.value = { name: '', description: '', category: 'bgp', vendor: 'frr_linux' }
}

function addField(sectionId: number) {
  const section = sections.value.find(s => s.id === sectionId)
  if (section) {
    section.fields.push({
      id: Date.now(),
      label: '',
      type: 'text',
      required: false,
      defaultValue: ''
    })
  }
}

function removeField(sectionId: number, fieldId: number) {
  const section = sections.value.find(s => s.id === sectionId)
  if (section) {
    section.fields = section.fields.filter(f => f.id !== fieldId)
  }
}
</script>

<template>
  <Modal :open="open" title="Visual Template Builder" size="xl" @close="emit('close')">
    <div class="space-y-6">
      <!-- Basic Info -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Template Name *</label>
          <input
            v-model="form.name"
            type="text"
            required
            placeholder="e.g., FRR BGP Configuration"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Vendor</label>
          <select
            v-model="form.vendor"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
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
      
      <div>
        <label class="block text-sm font-medium mb-1">Description</label>
        <input
          v-model="form.description"
          type="text"
          placeholder="Brief description of this template"
          class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label class="block text-sm font-medium mb-1">Category</label>
        <select
          v-model="form.category"
          class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="bgp">BGP</option>
          <option value="ospf">OSPF</option>
          <option value="interface">Interface</option>
          <option value="routing">Routing</option>
          <option value="vlan">VLAN</option>
          <option value="firewall">Firewall</option>
          <option value="nat">NAT</option>
          <option value="vpn">VPN</option>
          <option value="qos">QoS</option>
          <option value="other">Other</option>
        </select>
      </div>

      <!-- Template Sections -->
      <div class="border-t border-slate-600 pt-4">
        <h3 class="text-lg font-medium mb-4">Template Configuration</h3>
        
        <div v-for="section in sections" :key="section.id" class="mb-6 p-4 bg-slate-700/50 rounded-lg">
          <div class="flex items-center gap-3 mb-4">
            <input
              type="checkbox"
              v-model="section.enabled"
              class="w-4 h-4 rounded"
            />
            <h4 class="font-medium">{{ section.title }}</h4>
          </div>
          
          <div v-if="section.enabled" class="pl-7 space-y-3">
            <!-- Fixed Fields based on section -->
            <template v-if="section.id === 1">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-slate-400 mb-1">AS Number *</label>
                  <input
                    v-model="section.fields[0].defaultValue"
                    type="number"
                    placeholder="65001"
                    class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-slate-400 mb-1">Router ID *</label>
                  <input
                    v-model="section.fields[1].defaultValue"
                    type="text"
                    placeholder="10.0.0.1"
                    class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </template>
            
            <template v-if="section.id === 2">
              <div class="bg-slate-800 p-3 rounded-lg text-sm">
                <p class="text-slate-400 mb-2">Neighbor Configuration (Dynamic Array):</p>
                <ul class="list-disc list-inside text-slate-300 space-y-1">
                  <li>Neighbor IP</li>
                  <li>Remote AS</li>
                  <li>Password (optional)</li>
                  <li>Route-Map In (optional)</li>
                  <li>Route-Map Out (optional)</li>
                </ul>
                <p class="text-xs text-slate-500 mt-2">Users can add multiple neighbors when using this template</p>
              </div>
            </template>
            
            <template v-if="section.id === 3">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Address Family Type</label>
                <select
                  class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ipv4">IPv4 Only</option>
                  <option value="ipv6">IPv6 Only</option>
                  <option value="both">Both IPv4 and IPv6</option>
                </select>
                <p class="text-xs text-slate-500 mt-1">Users can select address family and add networks</p>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Preview Button -->
      <div class="flex justify-between items-center">
        <AppButton variant="ghost" @click="preview">
          <Eye class="w-4 h-4" />
          Preview Code
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
  <Modal :open="showPreview" title="Generated Template Code" size="xl" @close="showPreview = false">
    <div class="space-y-4">
      <div>
        <h4 class="text-sm font-medium text-slate-400 mb-2">Generated Jinja2 Template:</h4>
        <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-64">{{ previewContent }}</pre>
      </div>
      <div>
        <h4 class="text-sm font-medium text-slate-400 mb-2">Generated Variables:</h4>
        <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-64">{{ JSON.stringify(generatedVariables, null, 2) }}</pre>
      </div>
    </div>
  </Modal>
</template>
