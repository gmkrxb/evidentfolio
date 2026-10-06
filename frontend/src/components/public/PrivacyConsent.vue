<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { ShieldCheck } from 'lucide-vue-next'
import { privacy, loadPrivacy, savePrivacy } from '@/stores/privacy'
import { useLocaleStore } from '@/stores/locale'
const locale = useLocaleStore()
const dialog = ref<HTMLDialogElement>()
const managing = ref(false)
const analytics = ref(false)
const rawIp = ref(false)
const saving = ref(false)
const error = ref('')
const text = (zh: string, en: string) => locale.isEnglish ? en : zh
watch(analytics, (allowed) => { if (!allowed) rawIp.value = false })
watch(() => privacy.open, async (open) => {
  await nextTick()
  if (open) {
    analytics.value = privacy.analytics; rawIp.value = privacy.raw_ip; error.value = ''
    // 首次访问以不打断阅读的浮层出现；从页脚主动打开时才使用模态对话框。
    if (privacy.decided) dialog.value?.showModal()
    else dialog.value?.show()
  } else dialog.value?.close()
})
async function save(allow: boolean, ip = false) {
  saving.value = true; error.value = ''
  try { await savePrivacy(allow, ip); managing.value = false }
  catch { error.value = text('无法保存偏好，请重试；当前不进行访问统计。', 'Could not save. Please retry. Analytics remains off.'); privacy.analytics = false }
  finally { saving.value = false }
}
onMounted(loadPrivacy)
</script>
<template>
  <Teleport to="body">
    <dialog ref="dialog" class="privacy-dialog" :class="{ 'is-banner': !privacy.decided }" aria-labelledby="privacy-title" @cancel.prevent="privacy.decided && !saving && (privacy.open = false)">
      <ShieldCheck :size="28" class="privacy-icon" />
      <h2 id="privacy-title">{{ text('你的隐私，由你选择', 'Your privacy. Your choice.') }}</h2>
      <p>{{ text('必要 Cookie 用于登录和记住隐私选择。经你允许后，我们才使用统计 Cookie 记录浏览行为；原始 IP 地址单独征求同意，仅供站点管理员查看。', 'Essential cookies support sign-in and remember your choices. Analytics cookies record browsing only with your permission. Original IP addresses require separate consent and are visible only to the site administrator.') }}</p>
      <div v-if="managing" class="privacy-options">
        <label><span><strong>{{ text('必要 Cookie', 'Essential cookies') }}</strong><small>{{ text('登录安全与隐私偏好，始终启用', 'Sign-in security and privacy preferences, always on') }}</small></span><input type="checkbox" checked disabled /></label>
        <label><span><strong>{{ text('访问统计', 'Analytics') }}</strong><small>{{ text('页面访问、设备信息及访问路径', 'Page views, device information and journeys') }}</small></span><input v-model="analytics" type="checkbox" /></label>
        <label><span><strong>{{ text('原始 IP 与地区', 'Original IP and location') }}</strong><small>{{ text('加密保存 IP；可能向 IP 地区查询服务发送该地址。撤回时清除当前访客的已存 IP。', 'Store the IP encrypted; the address may be sent to an IP location service. Withdrawing clears stored IPs for this visitor.') }}</small></span><input v-model="rawIp" type="checkbox" :disabled="!analytics" /></label>
      </div>
      <p>{{ text('可随时在页脚的“隐私设置”修改选择。', 'Change your choices anytime in Privacy settings in the footer.') }}</p>
      <p v-if="error" role="alert" class="form-error">{{ error }}</p>
      <div class="privacy-actions">
        <button class="button button--outline" :disabled="saving" @click="save(false)">{{ text('拒绝非必要', 'Reject optional') }}</button>
        <button v-if="!managing" class="button button--outline" :disabled="saving" @click="managing = true">{{ text('管理偏好', 'Manage preferences') }}</button>
        <button v-else class="button button--outline" :disabled="saving" @click="save(analytics, rawIp)">{{ text('保存选择', 'Save choices') }}</button>
        <button class="button button--dark" :disabled="saving" @click="save(true, true)">{{ text('接受全部', 'Accept all') }}</button>
      </div>
      <button v-if="privacy.decided" class="privacy-close" :disabled="saving" @click="privacy.open = false">{{ text('取消', 'Cancel') }}</button>
    </dialog>
  </Teleport>
</template>
<style scoped>
.privacy-dialog{position:fixed;inset:auto 24px 24px auto;width:min(560px,calc(100vw - 32px));max-height:90dvh;overflow:auto;padding:30px;border:1px solid var(--color-line);border-radius:16px;background:var(--color-surface-strong);color:var(--color-ink);box-shadow:0 24px 100px #0003;margin:0}.privacy-dialog::backdrop{background:rgb(20 18 15 / 18%);backdrop-filter:blur(4px)}.privacy-dialog.is-banner{z-index:200;inset:auto auto 20px 20px;width:min(440px,calc(100vw - 32px));padding:22px 24px;border-radius:20px;background:color-mix(in srgb,var(--color-surface-strong) 88%,transparent);backdrop-filter:blur(18px) saturate(1.3);box-shadow:0 30px 80px -30px rgb(30 20 10 / 35%);animation:privacy-in .9s cubic-bezier(.16,1,.3,1) .8s both}.privacy-dialog.is-banner h2{font-size:19px;margin:10px 0 8px}.privacy-dialog.is-banner p{font-size:12.5px;line-height:1.7;margin:0 0 6px}.privacy-dialog.is-banner .privacy-icon{width:22px;height:22px}.privacy-dialog.is-banner .privacy-actions{margin-top:14px;gap:8px}.privacy-dialog.is-banner .privacy-actions .button{min-height:38px;padding:0 12px}@keyframes privacy-in{from{opacity:0;transform:translateY(24px)}}.privacy-icon{color:var(--color-brand)}.privacy-dialog h2{font-size:24px;letter-spacing:-.04em;margin:14px 0}.privacy-dialog p{font-size:13px;line-height:1.8;color:var(--color-ink-soft)}.privacy-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}.privacy-actions .button{flex:1;white-space:nowrap;font-size:12px;padding:12px}.privacy-options label{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:14px 0;border-bottom:1px solid var(--color-line)}.privacy-options small{display:block;margin-top:5px;line-height:1.5;color:var(--color-ink-soft)}.privacy-options input{width:18px;height:18px;flex-shrink:0}.privacy-close{display:block;margin:14px auto 0;font-size:12px}@media(max-width:600px){.privacy-dialog{inset:auto 16px 16px;padding:22px}.privacy-actions{flex-direction:column}}
</style>
