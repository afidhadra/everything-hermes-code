# Vue 3/TypeScript Development Skill

Best practices for Vue 3 with TypeScript.

## Project Structure

```text
src/
├── assets/          # Static files
├── components/      # Reusable components
│   ├── ui/         # Base UI components
│   └── features/   # Feature-specific components
├── composables/     # Composition API functions
├── layouts/         # Layout components
├── pages/           # Route components
├── stores/          # Pinia stores
├── types/           # TypeScript types
└── utils/           # Utility functions
```

## Composition API

### Setup Script

```vue
<script setup lang="ts">
// Props with type safety
interface Props {
  title: string
  count?: number
}

const props = withDefaults(defineProps<Props>(), {
  count: 0
})

// Emits
const emit = defineEmits<{
  update: [value: number]
  submit: [data: FormData]
}>()

// Reactive state
const count = ref(props.count)
const doubled = computed(() => count.value * 2)

// Methods
function increment() {
  count.value++
  emit('update', count.value)
}

// Watch
watch(count, (newVal, oldVal) => {
  console.log(`Count changed from ${oldVal} to ${newVal}`)
})

// Lifecycle
onMounted(() => {
  console.log('Component mounted')
})
</script>
```

### Composables

```typescript
// composables/useCounter.ts
export function useCounter(initialValue = 0) {
  const count = ref(initialValue)
  
  function increment() {
    count.value++
  }
  
  function decrement() {
    count.value--
  }
  
  function reset() {
    count.value = initialValue
  }
  
  return {
    count: readonly(count),
    increment,
    decrement,
    reset
  }
}

// Usage in component
const { count, increment } = useCounter(10)
```

## Pinia Stores

### Setup Store

```typescript
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string>('')
  
  // Getters
  const isAuthenticated = computed(() => !!user.value)
  const fullName = computed(() => 
    user.value ? `${user.value.firstName} ${user.value.lastName}` : ''
  )
  
  // Actions
  async function login(credentials: LoginCredentials) {
    try {
      const response = await api.login(credentials)
      user.value = response.user
      token.value = response.token
    } catch (error) {
      throw new Error('Login failed')
    }
  }
  
  function logout() {
    user.value = null
    token.value = ''
  }
  
  return {
    user: readonly(user),
    token: readonly(token),
    isAuthenticated,
    fullName,
    login,
    logout
  }
})
```

## TypeScript Integration

### Type Definitions

```typescript
// types/index.ts
export interface User {
  id: number
  email: string
  firstName: string
  lastName: string
  role: 'admin' | 'user'
}

export interface ApiResponse<T> {
  data: T
  message: string
  status: number
}

export type LoginCredentials = Pick<User, 'email'> & {
  password: string
}
```

### Props Types

```typescript
// Component props with TypeScript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false
})
```

## Best Practices

### Component Design

```vue
<template>
  <!-- Use kebab-case for components -->
  <user-card 
    :user="user" 
    @click="handleClick"
  />
</template>

<script setup lang="ts">
// Single responsibility
// Keep components small and focused
// Use composables for reusable logic
</script>

<style scoped>
/* Use scoped styles */
/* Follow BEM naming convention */
</style>
```

### Performance

```typescript
// Lazy loading components
const HeavyComponent = defineAsyncComponent(() =>
  import('./components/HeavyComponent.vue')
)

// Virtual scrolling for large lists
import { useVirtualList } from '@vueuse/core'

// Debounce expensive operations
import { useDebounceFn } from '@vueuse/core'

const debouncedSearch = useDebounceFn((query: string) => {
  search(query)
}, 300)
```

## Tools

### Essential

- `vue-tsc` — TypeScript checker
- `eslint` — Linting
- `prettier` — Formatting
- `vitest` — Unit testing
- `playwright` — E2E testing

### Development

- `vite` — Build tool
- `unplugin-auto-import` — Auto imports
- `unplugin-vue-components` — Auto components
