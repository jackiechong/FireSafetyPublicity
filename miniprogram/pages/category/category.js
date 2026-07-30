const { request } = require("../../utils/request");

function normalizeArticle(row = {}) {
  return {
    id: row.id || 0,
    title: row.title || "栏目内容",
    content: row.content || "请在网页端知识专栏维护栏目内容。",
    image_url: resolveAssetUrl(row.image_url || ""),
    video_url: resolveAssetUrl(row.video_url || ""),
    created_at: row.created_at || "",
  };
}

function resolveAssetUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  const app = getApp();
  const apiBase = (app.globalData.apiBase || require("../../utils/config").apiBase || "").replace(/\/+$/, "");
  return `${apiBase}${url}`;
}

Page({
  data: {
    code: "",
    name: "栏目内容",
    isVideoCategory: false,
    loading: true,
    articles: [],
  },

  onLoad(options = {}) {
    const code = decodeURIComponent(options.code || "");
    const name = decodeURIComponent(options.name || "栏目内容");
    this.setData({ code, name, isVideoCategory: code === "video" });
    wx.setNavigationBarTitle({ title: name });
    this.loadArticles(code);
  },

  async loadArticles(code) {
    if (!code) {
      this.setData({ loading: false, articles: [] });
      return;
    }
    this.setData({ loading: true });
    try {
      const rows = await request({ url: `/api/mp/knowledge-articles?category=${encodeURIComponent(code)}` });
      this.setData({ articles: (rows || []).map(normalizeArticle) });
    } catch (e) {
      wx.showToast({ title: e.message || "内容加载失败", icon: "none" });
      this.setData({ articles: [] });
    } finally {
      this.setData({ loading: false });
    }
  },
});
