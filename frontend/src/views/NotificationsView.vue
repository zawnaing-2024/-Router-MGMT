<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { notificationApi } from '@/api'
import type { NotificationChannel, Webhook } from '@/types'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'

const activeTab = ref('channels')
const channels = ref<NotificationChannel[]>([])
const webhooks = ref<Webhook[]>([])
const loading = ref(false)
const showChannelModal = ref(false)
const showWebhookModal = ref(false)
const editingChannel = ref<NotificationChannel | null>(null)
const editingWebhook = ref<Webhook | null>(null)

const channelForm = ref({
  name: '',
  channel_type: 'slack',
  config: {} as Record<string, any>,
  enabled: true,
  events: [] as string[]
})

const webhookForm = ref({
  name: '',
  url: '',
  events: [] as string[],
  headers: {} as Record<string, string>,
  enabled: true,
  retry_count: 3
})

const events = [
  'router.offline',
  'router.online',
  'backup.failed',
  'backup.success',
  'job.failed',
  'job.success',
  'config.changed'
]

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [channelsRes, webhooksRes] = await Promise.all([
      notificationApi.listChannels(),
      notificationApi.listWebhooks()
    ])
    channels.value = channelsRes.data
    webhooks.value = webhooksRes.data
  } catch (error) {
    console.error('Failed to load data:', error)
  }
  loading.value = false
}

function openChannelCreate() {
  editingChannel.value = null
  channelForm.value = { name: '', channel_type: 'slack', config: {}, enabled: true, events: [] }
  showChannelModal.value = true
}

function openChannelEdit(channel: NotificationChannel) {
  editingChannel.value = channel
  channelForm.value = {
    name: channel.name,
    channel_type: channel.channel_type,
    config: { ...channel.config },
    enabled: channel.enabled,
    events: [...channel.events]
  }
  showChannelModal.value = true
}

async function saveChannel() {
  try {
    const data = {
      name: channelForm.value.name,
      channel_type: channelForm.value.channel_type,
      config: channelForm.value.config,
      enabled: channelForm.value.enabled,
      events: channelForm.value.events
    }
    if (editingChannel.value) {
      await notificationApi.updateChannel(editingChannel.value.id, data)
    } else {
      await notificationApi.createChannel(data)
    }
    showChannelModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save channel:', error)
    alert('Failed to save channel: ' + (error as any).message)
  }
}

async function deleteChannel(id: number) {
  if (confirm('Are you sure you want to delete this channel?')) {
    try {
      await notificationApi.deleteChannel(id)
      await loadData()
    } catch (error) {
      console.error('Failed to delete channel:', error)
    }
  }
}

async function testChannel(id: number) {
  try {
    const res = await notificationApi.testChannel(id)
    alert(res.data.success ? 'Test successful!' : `Test failed: ${res.data.error}`)
  } catch (error) {
    alert('Test failed')
  }
}

function openWebhookCreate() {
  editingWebhook.value = null
  webhookForm.value = { name: '', url: '', events: [], headers: {}, enabled: true, retry_count: 3 }
  showWebhookModal.value = true
}

async function saveWebhook() {
  try {
    if (editingWebhook.value) {
      await notificationApi.updateWebhook(editingWebhook.value.id, webhookForm.value)
    } else {
      await notificationApi.createWebhook(webhookForm.value)
    }
    showWebhookModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save webhook:', error)
  }
}

async function deleteWebhook(id: number) {
  if (confirm('Are you sure you want to delete this webhook?')) {
    try {
      await notificationApi.deleteWebhook(id)
      await loadData()
    } catch (error) {
      console.error('Failed to delete webhook:', error)
    }
  }
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Notifications" description="Configure alerts and webhooks" />

    <div class="flex gap-2 mb-6">
      <button
        @click="activeTab = 'channels'"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'channels' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Channels
      </button>
      <button
        @click="activeTab = 'webhooks'"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'webhooks' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Webhooks
      </button>
    </div>

    <div v-if="activeTab === 'channels'">
      <div class="flex justify-end mb-4">
        <button
          @click="openChannelCreate"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Add Channel
        </button>
      </div>

      <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

      <div v-else-if="channels.length === 0" class="text-center py-12">
        <p class="text-slate-400 mb-4">No notification channels configured</p>
        <button
          @click="openChannelCreate"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Add your first channel
        </button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="channel in channels"
          :key="channel.id"
          class="bg-slate-800 rounded-lg p-4 border border-slate-700"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span
                :class="[
                  'w-3 h-3 rounded-full',
                  channel.enabled ? 'bg-green-500' : 'bg-slate-500'
                ]"
              ></span>
              <div>
                <span class="font-medium">{{ channel.name }}</span>
                <span class="ml-2 px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400">
                  {{ channel.channel_type }}
                </span>
              </div>
            </div>
            <div class="flex gap-2">
              <button @click="testChannel(channel.id)" class="text-blue-400 hover:text-blue-300 text-sm">
                Test
              </button>
              <button @click="openChannelEdit(channel)" class="text-slate-400 hover:text-slate-300 text-sm">
                Edit
              </button>
              <button @click="deleteChannel(channel.id)" class="text-red-400 hover:text-red-300 text-sm">
                Delete
              </button>
            </div>
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <span
              v-for="event in channel.events"
              :key="event"
              class="px-2 py-0.5 bg-slate-700 rounded text-xs"
            >
              {{ event }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'webhooks'">
      <div class="flex justify-end mb-4">
        <button
          @click="openWebhookCreate"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Add Webhook
        </button>
      </div>

      <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

      <div v-else-if="webhooks.length === 0" class="text-center py-12">
        <p class="text-slate-400 mb-4">No webhooks configured</p>
        <button
          @click="openWebhookCreate"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Add your first webhook
        </button>
      </div>

      <div v-else class="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table class="w-full">
          <thead class="bg-slate-700/50">
            <tr>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Name</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">URL</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Events</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Status</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-700">
            <tr v-for="webhook in webhooks" :key="webhook.id" class="hover:bg-slate-700/30">
              <td class="px-4 py-3 font-medium">{{ webhook.name }}</td>
              <td class="px-4 py-3 text-slate-400 text-sm max-w-xs truncate">{{ webhook.url }}</td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1">
                  <span v-for="event in webhook.events.slice(0, 2)" :key="event" class="px-1.5 py-0.5 bg-slate-700 rounded text-xs">
                    {{ event }}
                  </span>
                  <span v-if="webhook.events.length > 2" class="text-xs text-slate-500">
                    +{{ webhook.events.length - 2 }}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <span
                  :class="[
                    'px-2 py-1 rounded text-xs',
                    webhook.enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-400'
                  ]"
                >
                  {{ webhook.enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </td>
              <td class="px-4 py-3">
                <button @click="deleteWebhook(webhook.id)" class="text-red-400 hover:text-red-300 text-sm">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Modal :show="showChannelModal" :title="editingChannel ? 'Edit Channel' : 'Add Channel'" @close="showChannelModal = false">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Name</label>
          <input
            v-model="channelForm.name"
            type="text"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Type</label>
          <select v-model="channelForm.channel_type" class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600">
            <option value="slack">Slack</option>
            <option value="telegram">Telegram</option>
            <option value="email">Email</option>
            <option value="webhook">Webhook</option>
          </select>
        </div>

        <div v-if="channelForm.channel_type === 'slack'">
          <label class="block text-sm font-medium text-slate-300 mb-1">Webhook URL</label>
          <input
            v-model="channelForm.config.webhook_url"
            type="text"
            placeholder="https://hooks.slack.com/..."
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
          />
        </div>

        <div v-if="channelForm.channel_type === 'telegram'">
          <div class="space-y-3">
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Bot Token</label>
              <input
                v-model="channelForm.config.bot_token"
                type="text"
                placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
              />
              <p class="text-xs text-slate-500 mt-1">Get bot token from @BotFather on Telegram</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Chat ID</label>
              <input
                v-model="channelForm.config.chat_id"
                type="text"
                placeholder="123456789"
                class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
              />
              <p class="text-xs text-slate-500 mt-1">Get chat ID from @userinfobot on Telegram</p>
            </div>
          </div>
        </div>

        <div v-if="channelForm.channel_type === 'email'">
          <label class="block text-sm font-medium text-slate-300 mb-1">SMTP Config</label>
          <textarea
            v-model="channelForm.config.smtp_config"
            rows="3"
            placeholder="SMTP server, port, username, password..."
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
          ></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Events</label>
          <div class="space-y-2">
            <label v-for="event in events" :key="event" class="flex items-center gap-2">
              <input
                type="checkbox"
                :checked="channelForm.events.includes(event)"
                @change="
                  channelForm.events.includes(event)
                    ? channelForm.events = channelForm.events.filter(e => e !== event)
                    : channelForm.events.push(event)
                "
                class="rounded"
              />
              <span class="text-sm">{{ event }}</span>
            </label>
          </div>
        </div>
      </div>

      <template #footer>
        <button @click="showChannelModal = false" class="px-4 py-2 text-slate-300 hover:bg-slate-700 rounded-lg">
          Cancel
        </button>
        <button @click="saveChannel" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg">
          Save
        </button>
      </template>
    </Modal>

    <Modal :show="showWebhookModal" :title="editingWebhook ? 'Edit Webhook' : 'Add Webhook'" @close="showWebhookModal = false">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Name</label>
          <input v-model="webhookForm.name" type="text" class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600" />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">URL</label>
          <input v-model="webhookForm.url" type="text" placeholder="https://..." class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600" />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Events</label>
          <div class="space-y-2">
            <label v-for="event in events" :key="event" class="flex items-center gap-2">
              <input
                type="checkbox"
                :checked="webhookForm.events.includes(event)"
                @change="
                  webhookForm.events.includes(event)
                    ? webhookForm.events = webhookForm.events.filter(e => e !== event)
                    : webhookForm.events.push(event)
                "
                class="rounded"
              />
              <span class="text-sm">{{ event }}</span>
            </label>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Retry Count</label>
          <input v-model.number="webhookForm.retry_count" type="number" min="0" max="10" class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600" />
        </div>
      </div>

      <template #footer>
        <button @click="showWebhookModal = false" class="px-4 py-2 text-slate-300 hover:bg-slate-700 rounded-lg">
          Cancel
        </button>
        <button @click="saveWebhook" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg">
          Save
        </button>
      </template>
    </Modal>
  </div>
</template>
