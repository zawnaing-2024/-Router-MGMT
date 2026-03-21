<script setup lang="ts">
import { ref, computed } from 'vue'
import { Plus, Trash2, Save, Eye, Send, Check } from 'lucide-vue-next'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [data: { name: string, description: string, category: string, vendor: string, content: string, variables: Record<string, any> }]
}>()

interface NeighborRow {
  id: number
  ip: string
  remote_as: string
  description: string
  password: string
  route_map_in: string
  route_map_out: string
}

const form = ref({
  name: 'FRR BGP Configuration',
  description: 'Basic BGP peer configuration',
  category: 'bgp',
  vendor: 'frr_linux'
})

const asNumber = ref('65001')
const routerId = ref('10.0.0.1')
const addressFamily = ref('ipv4')

const neighbors = ref<NeighborRow[]>([
  { id: 1, ip: '', remote_as: '', description: '', password: '', route_map_in: '', route_map_out: '' }
])

const networks = ref<string[]>(['10.0.0.0/24'])

const generatedContent = computed(() => {
  let content = `router bgp ${asNumber.value}
 bgp router-id ${routerId.value}
!
`
  
  for (const neighbor of neighbors.value) {
    if (!neighbor.ip || !neighbor.remote_as) continue
    
    content += ` neighbor ${neighbor.ip} remote-as ${neighbor.remote_as}
`
    if (neighbor.description) {
      content += ` neighbor ${neighbor.ip} description ${neighbor.description}
`
    }
    if (neighbor.password) {
      content += ` neighbor ${neighbor.ip} password ${neighbor.password}
`
    }
  }
  
  content += `!
 address-family ipv${addressFamily.value === 'ipv6' ? '6' : '4'} unicast
`
  
  for (const neighbor of neighbors.value) {
    if (!neighbor.ip || !neighbor.remote_as) continue
    content += `  neighbor ${neighbor.ip} activate
`
    if (neighbor.route_map_in) {
      content += `  neighbor ${neighbor.ip} route-map ${neighbor.route_map_in} in
`
    }
    if (neighbor.route_map_out) {
      content += `  neighbor ${neighbor.ip} route-map ${neighbor.route_map_out} out
`
    }
  }
  
  content += `!
`
  
  return content
})

const generatedVariables = computed(() => {
  return {
    as_number: { type: 'number', label: 'AS Number', required: true, default: asNumber.value },
    router_id: { type: 'string', label: 'Router ID', required: true, default: routerId.value },
    address_family: { 
      type: 'string', 
      label: 'Address Family', 
      options: ['ipv4', 'ipv6'], 
      default: addressFamily.value 
    },
    neighbors: {
      type: 'array',
      label: 'BGP Neighbors',
      properties: {
        ip: { type: 'string', label: 'Neighbor IP' },
        remote_as: { type: 'number', label: 'Remote AS' },
        description: { type: 'string', label: 'Description' },
        password: { type: 'string', label: 'Password (optional)' },
        route_map_in: { type: 'string', label: 'Route-Map In (optional)' },
        route_map_out: { type: 'string', label: 'Route-Map Out (optional)' }
      }
    }
  }
})

const showPreview = ref(false)
const previewType = ref<'template' | 'config'>('config')

function addNeighbor() {
  neighbors.value.push({
    id: Date.now(),
    ip: '',
    remote_as: '',
    description: '',
    password: '',
    route_map_in: '',
    route_map_out: ''
  })
}

function removeNeighbor(id: number) {
  if (neighbors.value.length > 1) {
    neighbors.value = neighbors.value.filter(n => n.id !== id)
  }
}

function preview(type: 'template' | 'config') {
  previewType.value = type
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
}
</script>

<template>
  <Modal :open="open" title="Create BGP Configuration" size="xl" @close="emit('close')">
    <div class="space-y-6">
      <!-- Template Info -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Template Name *</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Vendor</label>
          <select v-model="form.vendor" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg">
            <option value="frr_linux">FRR Linux</option>
            <option value="cisco_ios">Cisco IOS</option>
            <option value="cisco_ios_xe">Cisco IOS-XE</option>
          </select>
        </div>
      </div>

      <!-- BGP Basic Config -->
      <div class="bg-slate-700/50 p-4 rounded-lg">
        <h3 class="font-medium mb-4 text-cyan-400">BGP Basic Configuration</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">AS Number *</label>
            <input
              v-model="asNumber"
              type="number"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="65001"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Router ID *</label>
            <input
              v-model="routerId"
              type="text"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="10.0.0.1"
            />
          </div>
        </div>
      </div>

      <!-- Neighbors Table -->
      <div class="bg-slate-700/50 p-4 rounded-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-medium text-cyan-400">BGP Neighbors</h3>
          <AppButton size="sm" @click="addNeighbor">
            <Plus class="w-4 h-4" />
            Add Neighbor
          </AppButton>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-slate-400 border-b border-slate-600">
                <th class="pb-2 pr-2">Neighbor IP *</th>
                <th class="pb-2 pr-2">Remote AS *</th>
                <th class="pb-2 pr-2">Description</th>
                <th class="pb-2 pr-2">Password</th>
                <th class="pb-2 pr-2">Route-Map In</th>
                <th class="pb-2 pr-2">Route-Map Out</th>
                <th class="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="neighbor in neighbors" :key="neighbor.id" class="border-b border-slate-700/50">
                <td class="py-2 pr-2">
                  <input
                    v-model="neighbor.ip"
                    type="text"
                    placeholder="192.168.1.1"
                    class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </td>
                <td class="py-2 pr-2">
                  <input
                    v-model="neighbor.remote_as"
                    type="number"
                    placeholder="65002"
                    class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </td>
                <td class="py-2 pr-2">
                  <input
                    v-model="neighbor.description"
                    type="text"
                    placeholder="Description"
                    class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </td>
                <td class="py-2 pr-2">
                  <input
                    v-model="neighbor.password"
                    type="password"
                    placeholder="Optional"
                    class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </td>
                <td class="py-2 pr-2">
                  <input
                    v-model="neighbor.route_map_in"
                    type="text"
                    placeholder="RM_IN"
                    class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </td>
                <td class="py-2 pr-2">
                  <input
                    v-model="neighbor.route_map_out"
                    type="text"
                    placeholder="RM_OUT"
                    class="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </td>
                <td class="py-2">
                  <button
                    @click="removeNeighbor(neighbor.id)"
                    class="p-1 text-red-400 hover:text-red-300"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Address Family -->
      <div class="bg-slate-700/50 p-4 rounded-lg">
        <h3 class="font-medium mb-4 text-cyan-400">Address Family</h3>
        <div class="flex gap-4">
          <label class="flex items-center gap-2">
            <input type="radio" v-model="addressFamily" value="ipv4" class="w-4 h-4" />
            <span>IPv4 Unicast</span>
          </label>
          <label class="flex items-center gap-2">
            <input type="radio" v-model="addressFamily" value="ipv6" class="w-4 h-4" />
            <span>IPv6 Unicast</span>
          </label>
        </div>
      </div>

      <!-- Preview & Actions -->
      <div class="flex justify-between pt-4 border-t border-slate-600">
        <div class="flex gap-2">
          <AppButton variant="outline" @click="preview('config')">
            <Eye class="w-4 h-4" />
            Preview Config
          </AppButton>
          <AppButton variant="outline" @click="preview('template')">
            <Save class="w-4 h-4" />
            Preview Template
          </AppButton>
        </div>
      </div>
    </div>

    <template #footer>
      <AppButton variant="ghost" @click="emit('close')">Cancel</AppButton>
      <AppButton @click="save">
        <Check class="w-4 h-4" />
        Save Template
      </AppButton>
    </template>
  </Modal>

  <!-- Preview Modal -->
  <Modal :open="showPreview" :title="previewType === 'config' ? 'Generated Configuration' : 'Jinja2 Template'" size="xl" @close="showPreview = false">
    <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-96 whitespace-pre">{{ previewType === 'config' ? generatedContent : generatedContent }}</pre>
  </Modal>
</template>
