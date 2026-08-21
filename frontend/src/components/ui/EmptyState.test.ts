import { mount } from '@vue/test-utils'
import EmptyState from './EmptyState.vue'
import { createPinia } from 'pinia'

describe('EmptyState', () => {
  it('renders an explicit empty state and slot action', () => {
    const wrapper = mount(EmptyState, {
      props: { title: '暂无项目', description: '创建一个项目' },
      slots: { default: '<button>新建</button>' },
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.text()).toContain('暂无项目')
    expect(wrapper.text()).toContain('创建一个项目')
    expect(wrapper.get('button').text()).toBe('新建')
  })
})
