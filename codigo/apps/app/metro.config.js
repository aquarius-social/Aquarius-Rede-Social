// Metro config do app Expo.
// Máquina de dev com RAM limitada: limita os workers do bundler para reduzir o
// pico de memória (Metro estoura memória com poucos MB livres). Ver a memória
// do projeto "ambiente-ram-limitada". Ajuste para cima se rodar numa máquina folgada.
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
config.maxWorkers = 2;

module.exports = config;
