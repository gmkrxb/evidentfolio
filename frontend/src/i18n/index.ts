import zhCN from './messages/zh-CN'
import en from './messages/en'

export const messages = { 'zh-CN': zhCN, en }
export type MessageKey = keyof typeof zhCN
