import { defineComponent, h, nextTick, onMounted } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView, useRoute } from 'vue-router'
import { expect, test } from 'vitest'
import { useAsyncState } from './useAsync'
import { useLocaleReload } from './useLocaleReload'
import { withoutLocale } from '@/utils/pageNavigation'

test('同页切换语言保留标题和图片节点，等待新译文期间也保留旧内容', async () => {
  let finish!: (value: string) => void
  const page = defineComponent({
    setup() {
      const route = useRoute()
      const state = useAsyncState<string>({ keepPreviousData: true })
      function load() { return state.run(() => route.path.startsWith('/en') ? new Promise<string>(resolve => { finish = resolve }) : Promise.resolve('中文标题')) }
      onMounted(load)
      useLocaleReload(load)
      return () => state.loading.value ? h('div', 'loading') : h('article', [h('h1', state.data.value || ''), h('img', { src: '/same-image.png' })])
    },
  })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: page }, { path: '/en', component: page }] })
  await router.push('/')
  const wrapper = mount(defineComponent({ setup() { const route = useRoute(); return () => h(RouterView, { key: withoutLocale(route.path) }) } }), { global: { plugins: [router] } })
  await flushPromises()
  const heading = wrapper.get('h1').element, image = wrapper.get('img').element
  await router.push('/en')
  await nextTick()
  expect(wrapper.get('h1').text()).toBe('中文标题')
  expect(wrapper.get('h1').element).toBe(heading)
  finish('English title')
  await flushPromises()
  expect(wrapper.get('h1').text()).toBe('English title')
  expect(wrapper.get('h1').element).toBe(heading)
  expect(wrapper.get('img').element).toBe(image)
  wrapper.unmount()
})
