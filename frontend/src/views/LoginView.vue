<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { Lock, User } from 'lucide-vue-next'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function login() {
  if (!username.value || !password.value) {
    error.value = 'Please enter username and password'
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    const res = await axios.post('/api/auth/login', {
      username: username.value,
      password: password.value
    })
    
    localStorage.setItem('token', res.data.token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    router.push('/dashboard')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-900 flex items-center justify-center">
    <div class="w-full max-w-md">
      <div class="bg-slate-800 rounded-xl border border-slate-700 p-8">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-white">Router MGMT</h1>
          <p class="text-slate-400 mt-2">Sign in to continue</p>
        </div>
        
        <form @submit.prevent="login" class="space-y-4">
          <div>
            <label class="block text-sm text-slate-400 mb-1">Username</label>
            <div class="relative">
              <User class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                v-model="username"
                type="text"
                placeholder="Username"
                class="w-full bg-slate-700 border border-slate-600 rounded-lg pl-10 pr-4 py-3 text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          
          <div>
            <label class="block text-sm text-slate-400 mb-1">Password</label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                v-model="password"
                type="password"
                placeholder="Password"
                class="w-full bg-slate-700 border border-slate-600 rounded-lg pl-10 pr-4 py-3 text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          
          <div v-if="error" class="text-red-400 text-sm">
            {{ error }}
          </div>
          
          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 rounded-lg transition-colors disabled:opacity-50"
          >
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
