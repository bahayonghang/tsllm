import { Alert, Button } from "antd";
import { Component, type ReactNode, Suspense } from "react";

export class FeatureLoading extends Component<
  { children: ReactNode; label: string },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <Alert
          type="error"
          showIcon
          title={`${this.props.label}加载失败`}
          action={
            <Button
              href={`${window.location.pathname}${window.location.search}${window.location.hash}`}
            >
              重新加载页面
            </Button>
          }
        />
      );
    }
    return (
      <Suspense fallback={<div role="status">正在加载{this.props.label}…</div>}>
        {this.props.children}
      </Suspense>
    );
  }
}
