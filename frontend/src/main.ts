import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/global.css'
import './styles/experience.css'
import './styles/adaptive.css'
import './styles/scroll-story.css'
import './styles/atelier.css'
import './styles/home.css'
import { initializeTheme } from './stores/theme'
import { reveal } from './directives/reveal'
import { scrollProgress } from './directives/scrollProgress'
import { scramble } from './directives/scramble'
import { magnetic } from './directives/magnetic'
import { segment } from './directives/segment'
import { installImageRecovery } from './utils/imageRecovery'
import { protect } from './directives/protect'

initializeTheme()
installImageRecovery()
createApp(App).directive('reveal', reveal).directive('scroll-progress', scrollProgress).directive('scramble', scramble).directive('magnetic', magnetic).directive('segment', segment).directive('protect', protect).use(createPinia()).use(router).mount('#app')
