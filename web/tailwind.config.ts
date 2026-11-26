import type { Config } from 'tailwindcss';
const config: Config = { content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}'], theme: { extend: { colors: { ink:'#080d14', panel:'#101925', line:'#253448', muted:'#8292a6', accent:'#75b6f2', positive:'#19c995', negative:'#f16b78' } } }, plugins: [] };
export default config;
