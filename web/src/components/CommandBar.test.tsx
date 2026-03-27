import { render, screen, fireEvent } from "@testing-library/react";
import CommandBar from "./CommandBar";

describe("CommandBar", () => {
  it("renders the input and submit button", () => {
    render(<CommandBar onSubmit={jest.fn()} isLoading={false} />);
    expect(screen.getByPlaceholderText("Describe an action...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
  });

  it("calls onSubmit with trimmed input on form submit", () => {
    const onSubmit = jest.fn();
    render(<CommandBar onSubmit={onSubmit} isLoading={false} />);

    const input = screen.getByPlaceholderText("Describe an action...");
    fireEvent.change(input, { target: { value: "  categorize all  " } });
    fireEvent.submit(input.closest("form")!);

    expect(onSubmit).toHaveBeenCalledWith("categorize all");
  });

  it("clears input after submit", () => {
    render(<CommandBar onSubmit={jest.fn()} isLoading={false} />);

    const input = screen.getByPlaceholderText("Describe an action...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test" } });
    fireEvent.submit(input.closest("form")!);

    expect(input.value).toBe("");
  });

  it("does not submit empty input", () => {
    const onSubmit = jest.fn();
    render(<CommandBar onSubmit={onSubmit} isLoading={false} />);

    const input = screen.getByPlaceholderText("Describe an action...");
    fireEvent.submit(input.closest("form")!);

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables input and button when loading", () => {
    render(<CommandBar onSubmit={jest.fn()} isLoading={true} />);

    expect(screen.getByPlaceholderText("Describe an action...")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveTextContent("Running...");
  });
});
