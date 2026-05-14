// 与后端启动端口一致（默认 18080，见 backend/run.ps1）
// 开发者工具：详情 → 本地设置 → 不校验合法域名
// 真机调试需 HTTPS 域名并在小程序后台配置 request 合法域名
const apiBase = "http://127.0.0.1:18080";

module.exports = { apiBase };
