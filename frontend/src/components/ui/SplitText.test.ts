import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SplitText from './SplitText.vue'
import ProjectArt from '@/components/public/ProjectArt.vue'

describe('SplitText', () => {
  it('splits lines and keeps the full sentence for screen readers', () => {
    const wrapper = mount(SplitText, { props: { text: 'Structure is a poem.\nData is a trace.', mode: 'fill' } })
    expect(wrapper.findAll('.split-text__line')).toHaveLength(2)
    expect(wrapper.find('.sr-only').text()).toBe('Structure is a poem.\nData is a trace.')
    const indices = wrapper.findAll('.split-text__word').map((word) => Number((word.element as HTMLElement).style.getPropertyValue('--i')))
    expect(indices).toEqual([...indices].sort((a, b) => a - b))
  })
})

describe('ProjectArt', () => {
  it('draws the same map for the same project', () => {
    const first = mount(ProjectArt, { props: { seed: 'abc' } }).html()
    const second = mount(ProjectArt, { props: { seed: 'abc' } }).html()
    const other = mount(ProjectArt, { props: { seed: 'xyz' } }).html()
    expect(first).toBe(second)
    expect(first).not.toBe(other)
  })
})
