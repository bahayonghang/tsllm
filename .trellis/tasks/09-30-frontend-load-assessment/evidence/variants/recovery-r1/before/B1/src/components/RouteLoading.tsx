import { Alert, Button } from "antd";
import type { ComponentType } from "react";
import { useLocation } from "react-router";

export function RouteLoading() {
  return <div role="status">正在加载页面…</div>;
}

export function RouteLoadError() {
  const location = useLocation();
  return (
    <Alert
      type="error"
      showIcon
      title="页面加载失败"
      description="请重新加载页面。"
      action={
        <Button href={`${location.pathname}${location.search}${location.hash}`}>
          重新加载页面
        </Button>
      }
    />
  );
}

export function loadRoute(load: () => Promise<{ Component: ComponentType }>) {
  return async () => {
    try {
      return await load();
    } catch {
      return { Component: RouteLoadError };
    }
  };
}
