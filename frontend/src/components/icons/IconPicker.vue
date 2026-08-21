<script setup lang="ts">
import { computed, ref } from 'vue'
import { Image, Search, X } from 'lucide-vue-next'
import ConfiguredIcon from './ConfiguredIcon.vue'
import { iconRegistry } from '@/icons/registry'
import type { Asset } from '@/types'

const props = defineProps<{
  iconName: string
  iconSvg: string
  imageUuid: string
  assets: Asset[]
}>()
const emit = defineEmits<{
  'update:iconName': [value: string]
  'update:iconSvg': [value: string]
  'update:imageUuid': [value: string]
}>()
const search = ref('')
const expanded = ref(false)
const names = computed(() =>
  Object.keys(iconRegistry).filter((name) => name.toLowerCase().includes(search.value.toLowerCase())),
)
function choose(name: string) {
  emit('update:iconName', name)
  emit('update:iconSvg', '')
  emit('update:imageUuid', '')
}
function chooseImage(uuid: string) {
  emit('update:imageUuid', uuid)
  if (uuid) {
    emit('update:iconName', '')
    emit('update:iconSvg', '')
  }
}
function updateSvg(value: string) {
  emit('update:iconSvg', value)
  if (value) {
    emit('update:iconName', '')
    emit('update:imageUuid', '')
  }
}
</script>

<template>
  <div class="icon-picker">
    <button type="button" class="icon-picker__summary" @click="expanded = !expanded">
      <span><ConfiguredIcon :image-uuid="imageUuid" :icon-name="iconName" :icon-svg="iconSvg" :size="22" /></span>
      <span><strong>图标选择器</strong><small>{{ imageUuid ? '上传图片' : iconName || (iconSvg ? '自定义 SVG' : '未选择') }}</small></span>
      <X v-if="expanded" :size="16" /><Search v-else :size="16" />
    </button>
    <Transition name="picker-expand">
      <div v-if="expanded" class="icon-picker__panel">
        <label class="search-field"><Search :size="15" /><span class="sr-only">搜索 Element 图标</span><input v-model="search" placeholder="搜索 Element 图标名称" /></label>
        <div class="icon-picker__grid">
          <button v-for="name in names" :key="name" type="button" :class="{ active: iconName === name }" :title="name" @click="choose(name)">
            <ConfiguredIcon :icon-name="name" :size="20" /><span>{{ name }}</span>
          </button>
        </div>
        <label>
          <span><Image :size="15" />上传图片资源</span>
          <select :value="imageUuid" @change="chooseImage(($event.target as HTMLSelectElement).value)">
            <option value="">不使用上传图片</option>
            <option v-for="asset in assets" :key="asset.uuid" :value="asset.uuid">{{ asset.display_name }}</option>
          </select>
        </label>
        <label>
          安全 SVG 代码
          <textarea
            :value="iconSvg"
            rows="5"
            placeholder="<svg viewBox=&quot;0 0 24 24&quot;>...</svg>"
            @input="updateSvg(($event.target as HTMLTextAreaElement).value)"
          />
          <small>仅允许基础图形元素；脚本、事件、外链、样式和动画会被后端拒绝或移除。</small>
        </label>
      </div>
    </Transition>
  </div>
</template>

