const { request } = require("../../utils/request");

const FALLBACK_CATEGORIES = [
  { code: "knowledge", name: "消防知识" },
  { code: "video", name: "宣传视频" },
  { code: "system", name: "制度" },
  { code: "equipment", name: "器材使用" },
];

const PREFERRED_CODES = FALLBACK_CATEGORIES.map((item) => item.code);
const ICON_MAP = {
  knowledge: "📖",
  video: "▶",
  system: "▣",
  equipment: "🧯",
};
const COLOR_MAP = {
  knowledge: "blue",
  video: "orange",
  system: "green",
  equipment: "red",
};
const ACTIVITY_CATEGORY = { code: "activity", name: "热门活动" };

function normalizeArticle(row = {}) {
  const content = row.content || "请在网页端知识专栏维护栏目内容。";
  return {
    id: row.id || 0,
    category: row.category || "",
    title: row.title || "栏目内容",
    content,
    summary: content.replace(/\s+/g, " ").slice(0, 34),
    image_url: resolveAssetUrl(row.image_url || ""),
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
    loadingAction: "",
    bannerImageUrl: "",
    modules: [],
    activityArticles: [],
  },

  async onLoad() {
    this.setFallbackContent();
    await this.loadHomeContent();
  },

  onShow() {
    // 首页允许直接浏览，不主动登录、不跳转、不索取手机号/头像/昵称。
  },

  setFallbackContent() {
    const modules = FALLBACK_CATEGORIES.map((item, index) => ({
      ...item,
      key: item.code,
      title: item.name,
      icon: ICON_MAP[item.code] || "□",
      color: COLOR_MAP[item.code] || "blue",
    }));
    this.setData({
      modules,
      activityArticles: [
        normalizeArticle({ title: "119 消防宣传月", content: "学习培训 记录成长" }),
        normalizeArticle({ title: "消防安全知识学习", content: "掌握常识 防患未然" }),
      ],
    });
  },

  async loadHomeContent() {
    try {
      const homeConfig = await request({ url: "/api/mp/home-config" });
      this.setData({ bannerImageUrl: resolveAssetUrl(homeConfig?.banner_image_url || "") });
    } catch {
      // 顶部图未配置时继续使用默认绘制背景。
    }
    try {
      const categories = await request({ url: "/api/mp/knowledge-categories" });
      const source = categories && categories.length ? categories : FALLBACK_CATEGORIES;
      const byCode = (source || []).reduce((acc, item) => {
        acc[item.code] = item;
        return acc;
      }, {});
      const usableCategories = PREFERRED_CODES.map((code) => byCode[code] || FALLBACK_CATEGORIES.find((item) => item.code === code)).filter(Boolean);
      const modules = usableCategories.map((item) => ({
        ...item,
        key: item.code,
        title: item.name,
        icon: ICON_MAP[item.code] || "□",
        color: COLOR_MAP[item.code] || "blue",
      }));
      const articleGroups = await Promise.all(
        modules.map(async (item) => {
          try {
            const rows = await request({ url: `/api/mp/knowledge-articles?category=${encodeURIComponent(item.code)}` });
            return (rows || []).map(normalizeArticle);
          } catch {
            return [];
          }
        })
      );
      const allArticles = articleGroups.flat();
      let activityArticles = [];
      try {
        const activityRows = await request({ url: `/api/mp/knowledge-articles?category=${ACTIVITY_CATEGORY.code}` });
        activityArticles = (activityRows || []).map(normalizeArticle);
      } catch {
        activityArticles = [];
      }
      this.setData({
        modules,
        activityArticles: activityArticles.length ? activityArticles.slice(0, 2) : allArticles.length ? allArticles.slice(0, 2) : this.data.activityArticles,
      });
    } catch {
      // 保留默认可浏览内容。
    }
  },

  onPickModule(e) {
    const index = Number(e.currentTarget.dataset.index) || 0;
    const item = this.data.modules[index];
    if (!item) return;
    this.openCategory(item);
  },

  openActivities() {
    this.openCategory(ACTIVITY_CATEGORY);
  },

  openCategory(item) {
    const code = encodeURIComponent(item.code || "");
    const name = encodeURIComponent(item.name || item.title || "栏目内容");
    wx.navigateTo({ url: `/pages/category/category?code=${code}&name=${name}` });
  },

  goKnowledge() {
    this.openCategory({ code: "knowledge", name: "消防知识" });
  },

  async ensureLogin(nextUrl, action) {
    const app = getApp();
    if (app.globalData.token) {
      if (nextUrl.indexOf("/pages/checkin/checkin") === 0) {
        try {
          const me = await request({ url: "/api/mp/me" });
          const ok = me && me.name && me.phone && me.district_id && me.organization_id && me.job_title;
          if (!ok) {
            wx.navigateTo({ url: "/pages/bind/bind?redirect=checkin" });
            return;
          }
        } catch {
          app.setToken("");
        }
      }
      wx.navigateTo({ url: nextUrl });
      return;
    }
    this.setData({ loadingAction: action || "" });
    try {
      const login = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });
      const res = await request({
        url: "/api/mp/login",
        method: "POST",
        data: { code: login.code },
      });
      app.setToken(res.token);
      app.globalData.isAdmin = !!res.is_admin;
      let needsProfile = !!res.need_profile;
      if (!needsProfile && nextUrl.indexOf("/pages/checkin/checkin") === 0) {
        try {
          const me = await request({ url: "/api/mp/me" });
          needsProfile = !(me && me.name && me.phone && me.district_id && me.organization_id && me.job_title);
        } catch {
          needsProfile = true;
        }
      }
      if (needsProfile) {
        const q = nextUrl.indexOf("/pages/checkin/checkin") === 0 ? "?redirect=checkin" : "";
        wx.navigateTo({ url: `/pages/bind/bind${q}` });
      } else {
        wx.navigateTo({ url: nextUrl });
      }
    } catch (e) {
      wx.showToast({ title: e.message || "登录失败", icon: "none" });
    } finally {
      this.setData({ loadingAction: "" });
    }
  },

  goJoin() {
    this.ensureLogin("/pages/checkin/checkin", "join");
  },

  goMe() {
    this.ensureLogin("/pages/me/me", "me");
  },
});
