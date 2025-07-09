import { createRouter, createWebHashHistory } from 'vue-router';

import ChatPage from '../views/ChatPage.vue';

const routes = [
  {
    path: '/chat',
    name: 'Chat',
    component: ChatPage,
    meta: {
      title: '语音转写对话'
    }
  }
];

const router = createRouter({
  // 使用 hash 模式，URL 会带上 “#”
  history: createWebHashHistory(),
  routes
});

export default router;
