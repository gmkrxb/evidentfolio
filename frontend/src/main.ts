import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/global.css'
import { reveal } from './directives/reveal'
import { installImageRecovery } from './utils/imageRecovery'

installImageRecovery()
createApp(App).directive('reveal', reveal).use(createPinia()).use(router).mount('#app')
