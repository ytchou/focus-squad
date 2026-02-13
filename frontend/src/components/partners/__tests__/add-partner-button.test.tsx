import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AddPartnerButton } from "../add-partner-button";

describe("AddPartnerButton", () => {
  const defaultProps = {
    userId: "user-123",
    partnershipStatus: null,
    onSendRequest: vi.fn(),
  };

  it("renders 'Add Partner' state for non-partners", () => {
    render(<AddPartnerButton {...defaultProps} />);
    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent("Add Partner");
  });

  it("renders 'Pending' state for sent requests", () => {
    render(<AddPartnerButton {...defaultProps} partnershipStatus="pending" />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("Pending");
  });

  it("renders disabled state for existing partners", () => {
    render(<AddPartnerButton {...defaultProps} partnershipStatus="accepted" />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("Partners");
  });

  it("calls onSendRequest when clicked in default state", () => {
    const onSendRequest = vi.fn();
    render(<AddPartnerButton {...defaultProps} onSendRequest={onSendRequest} />);

    fireEvent.click(screen.getByRole("button"));
    expect(onSendRequest).toHaveBeenCalledWith("user-123");
  });

  it("disables button when status is pending", () => {
    render(<AddPartnerButton {...defaultProps} partnershipStatus="pending" />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("disables button when status is accepted", () => {
    render(<AddPartnerButton {...defaultProps} partnershipStatus="accepted" />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("renders compact variant without text", () => {
    render(<AddPartnerButton {...defaultProps} compact />);
    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
    // In compact mode, text is hidden
    expect(button).not.toHaveTextContent("Add Partner");
  });

  it("renders full variant with text", () => {
    render(<AddPartnerButton {...defaultProps} compact={false} />);
    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent("Add Partner");
  });
});
