const { request } = require("../../utils/request");

function resolveAssetUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  const app = getApp();
  const apiBase = (app.globalData.apiBase || require("../../utils/config").apiBase || "").replace(/\/+$/, "");
  return `${apiBase}${url}`;
}

function normalizeArticle(row = {}) {
  return {
    id: row.id || 0,
    category: row.category || "",
    title: row.title || "栏目内容",
    content: row.content || "",
    image_url: resolveAssetUrl(row.image_url || ""),
    video_url: resolveAssetUrl(row.video_url || ""),
  };
}

Page({
  data: {
    loading: true,
    article: normalizeArticle(),
  },

  onLoad(options = {}) {
    const app = getApp();
    const id = Number(decodeURIComponent(options.id || "0")) || 0;
    const category = decodeURIComponent(options.category || "");
    const cached = app.globalData.currentArticle;
    if (cached && Number(cached.id) === id) {
      const article = normalizeArticle(cached);
      this.setData({ article, loading: false });
      wx.setNavigationBarTitle({ title: article.title || "详情" });
      return;
    }
    this.loadArticle(id, category);
  },

  async loadArticle(id, category) {
    this.setData({ loading: true });
    try {
      const rows = await request({ url: `/api/mp/knowledge-articles?category=${encodeURIComponent(category)}` });
      const found = (rows || []).find((item) => Number(item.id) === id);
      const article = normalizeArticle(found || {});
      this.setData({ article });
      wx.setNavigationBarTitle({ title: article.title || "详情" });
    } catch (e) {
      wx.showToast({ title: e.message || "内容加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
});
