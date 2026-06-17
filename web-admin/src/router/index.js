import { createRouter, createWebHistory } from "vue-router";
import Login from "../views/Login.vue";
import Layout from "../views/Layout.vue";
import { prefersMobileDashboard } from "../utils/device";

const routes = [
  { path: "/login", name: "login", component: Login, meta: { public: true } },
  {
    path: "/h5",
    component: () => import("../views/h5/H5Shell.vue"),
    meta: { public: true, h5: true },
    children: [
      {
        path: "",
        redirect: "/h5/entry",
      },
      {
        path: "entry",
        name: "h5-entry",
        component: () => import("../views/h5/H5Entry.vue"),
        meta: { public: true, h5: true },
      },
      {
        path: "checkin",
        name: "h5-checkin",
        component: () => import("../views/h5/H5Checkin.vue"),
        meta: { public: true, h5: true },
      },
      {
        path: "bind",
        name: "h5-bind",
        component: () => import("../views/h5/H5Bind.vue"),
        meta: { public: true, h5: true },
      },
      {
        path: "me",
        name: "h5-me",
        component: () => import("../views/h5/H5Me.vue"),
        meta: { public: true, h5: true },
      },
    ],
  },
  {
    path: "/m",
    component: () => import("../views/mobile/MobileShell.vue"),
    children: [
      {
        path: "",
        name: "mobile",
        component: () => import("../views/mobile/MobileView.vue"),
      },
      {
        path: "admin",
        name: "mobile-admin",
        component: () => import("../views/mobile/MobileAdmin.vue"),
      },
    ],
  },
  {
    path: "/",
    component: Layout,
    children: [
      { path: "", redirect: "/dashboard" },
      {
        path: "dashboard",
        name: "dashboard",
        component: () => import("../views/Dashboard.vue"),
      },
      {
        path: "orgs",
        name: "orgs",
        component: () => import("../views/Organizations.vue"),
      },
      {
        path: "trainings",
        name: "trainings",
        component: () => import("../views/Trainings.vue"),
      },
      {
        path: "persons",
        name: "persons",
        component: () => import("../views/Persons.vue"),
      },
      {
        path: "stats",
        name: "stats",
        component: () => import("../views/Stats.vue"),
      },
      {
        path: "reports",
        name: "reports",
        component: () => import("../views/Reports.vue"),
      },
      {
        path: "knowledge",
        name: "knowledge",
        component: () => import("../views/KnowledgeArticles.vue"),
      },
      {
        path: "accounts",
        name: "accounts",
        component: () => import("../views/AdminAccounts.vue"),
      },
      {
        path: "dicts",
        name: "dicts",
        component: () => import("../views/DictionaryOptions.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("admin_token");
  const isPublic = to.matched.some((r) => r.meta.public);
  if (!isPublic && !token) {
    next({ name: "login", query: { redirect: to.fullPath } });
    return;
  }
  if (to.name === "login" && token) {
    const r = to.query.redirect;
    if (typeof r === "string" && r.startsWith("/") && !r.startsWith("//")) {
      next({ path: r });
      return;
    }
    next({ path: "/" });
    return;
  }

  // 手机 / 平板浏览器：自动进入 /m 数据看板，无需再点侧栏「手机看板」
  const mobileRouteNames = new Set(["mobile", "mobile-admin"]);
  if (token && !isPublic && to.name !== "login" && !mobileRouteNames.has(to.name) && prefersMobileDashboard()) {
    next({ path: "/m", replace: true });
    return;
  }

  next();
});

export default router;
