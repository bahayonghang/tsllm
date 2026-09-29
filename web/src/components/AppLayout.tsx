import { Layout, Menu, theme } from "antd";
import { Link, Outlet, useLocation } from "react-router";

const ITEMS = [
  { key: "/runs", label: <Link to="/runs">运行</Link> },
  { key: "/runs/new", label: <Link to="/runs/new">新建运行</Link> },
  { key: "/compare", label: <Link to="/compare">对比</Link> },
  { key: "/datasets", label: <Link to="/datasets">数据集</Link> },
  { key: "/system", label: <Link to="/system">系统</Link> },
];

function selectedKey(pathname: string): string {
  if (pathname === "/runs/new") return "/runs/new";
  const match = ITEMS.find((item) => item.key !== "/runs/new" && pathname.startsWith(item.key));
  return match?.key ?? "/runs";
}

export function AppLayout() {
  const { pathname } = useLocation();
  const { token } = theme.useToken();
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 16,
          height: "auto",
          paddingInline: 16,
          background: token.colorBgContainer,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <Link
          to="/runs"
          style={{
            fontWeight: 600,
            whiteSpace: "nowrap",
            color: token.colorText,
          }}
        >
          TSFM 实验平台
        </Link>
        {/* Items wrap on narrow screens; the overflow menu needs layout measurement to collapse. */}
        <Menu
          mode="horizontal"
          disabledOverflow
          selectedKeys={[selectedKey(pathname)]}
          items={ITEMS}
          style={{ flex: 1, minWidth: 0, flexWrap: "wrap", borderBottom: "none" }}
        />
      </Layout.Header>
      <Layout.Content style={{ padding: 16, maxWidth: 1600, width: "100%", margin: "0 auto" }}>
        <Outlet />
      </Layout.Content>
    </Layout>
  );
}
