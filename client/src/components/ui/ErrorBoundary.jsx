import { Component } from "react";
import Button from "./Button";
import styles from "./ErrorBoundary.module.css";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.container} role="alert">
          <h2 className={styles.heading}>Something went wrong</h2>
          <p className={styles.message}>
            An unexpected error occurred. Please try again.
          </p>
          <Button
            variant="secondary"
            onClick={() => this.setState({ hasError: false })}
          >
            Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
