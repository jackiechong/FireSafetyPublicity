export const NAV = [
  {
    group: '数据概览',
    items: [{ to: '/dashboard', label: '首页总览', icon: 'grid' }],
  },
  {
    group: '培训业务',
    items: [
      { to: '/trainings', label: '培训记录', icon: 'list' },
      { to: '/persons', label: '注册人员', icon: 'users' },
    ],
  },
  {
    group: '基础台账',
    items: [
      { to: '/orgs', label: '单位台账', icon: 'building' },
      { to: '/reports', label: '综合查询', icon: 'search' },
    ],
  },
  {
    group: '统计分析',
    items: [{ to: '/stats', label: '统计分析', icon: 'chart' }],
  },
  {
    group: '内容与系统',
    items: [
      { to: '/knowledge', label: '知识专栏', icon: 'book', roles: ['detachment'] },
      { to: '/accounts', label: '账号权限', icon: 'shield', roles: ['detachment'] },
      { to: '/dicts', label: '字典配置', icon: 'sliders', roles: ['detachment'] },
    ],
  },
  {
    group: '交付',
    items: [{ to: '/m', label: '学员端预览', icon: 'phone' }],
  },
];

export function findNavItem(path) {
  for (const g of NAV) {
    for (const it of g.items) {
      if (path === it.to || path.startsWith(it.to + '/')) {
        return { ...it, group: g.group };
      }
    }
  }
  return null;
}

export function visibleNav(role) {
  return NAV.map((g) => ({
    ...g,
    items: g.items.filter((it) => !it.roles || it.roles.includes(role)),
  })).filter((g) => g.items.length);
}
