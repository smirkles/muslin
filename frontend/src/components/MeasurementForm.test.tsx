import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MeasurementForm } from "./MeasurementForm";

const FIELD_LABELS = [
  "Full bust",
  "High bust",
  "Bust point to bust point",
  "Waist",
  "Hip",
  "Height",
  "Back length",
];

const VALID_VALUES = {
  "Full bust": "96",
  "High bust": "85",
  "Bust point to bust point": "18",
  Waist: "78",
  Hip: "104",
  Height: "168",
  "Back length": "39.5",
};

function fillAllFields(user: ReturnType<typeof userEvent.setup>) {
  return async () => {
    for (const [label, value] of Object.entries(VALID_VALUES)) {
      const input = screen.getByLabelText(new RegExp(label, "i"));
      await user.clear(input);
      await user.type(input, value);
    }
  };
}

describe("MeasurementForm", () => {
  describe("rendering", () => {
    it("renders all 7 labelled fields", () => {
      render(<MeasurementForm onSubmit={vi.fn()} />);
      FIELD_LABELS.forEach((label) => {
        expect(screen.getByLabelText(new RegExp(label, "i"))).toBeTruthy();
      });
    });

    it("renders a submit button", () => {
      render(<MeasurementForm onSubmit={vi.fn()} />);
      expect(screen.getByRole("button", { name: /calculate my fit/i })).toBeTruthy();
    });

    it("submit button is disabled when fields are empty", () => {
      render(<MeasurementForm onSubmit={vi.fn()} />);
      const btn = screen.getByRole("button", { name: /calculate my fit/i });
      expect(btn).toBeDisabled();
    });
  });

  describe("validation on blur", () => {
    it("shows error for bust_cm below minimum after blur", async () => {
      const user = userEvent.setup();
      render(<MeasurementForm onSubmit={vi.fn()} />);
      const input = screen.getByLabelText(/full bust/i);
      await user.clear(input);
      await user.type(input, "59");
      await user.tab();
      expect(screen.getByText(/must be between/i)).toBeTruthy();
    });

    it("shows error for apex_to_apex_cm below minimum after blur", async () => {
      const user = userEvent.setup();
      render(<MeasurementForm onSubmit={vi.fn()} />);
      const input = screen.getByLabelText(/bust point to bust point/i);
      await user.clear(input);
      await user.type(input, "9");
      await user.tab();
      expect(screen.getByText(/must be between/i)).toBeTruthy();
    });

    it("shows error for high_bust_cm above maximum after blur", async () => {
      const user = userEvent.setup();
      render(<MeasurementForm onSubmit={vi.fn()} />);
      const input = screen.getByLabelText(/high bust/i);
      await user.clear(input);
      await user.type(input, "201");
      await user.tab();
      expect(screen.getByText(/must be between/i)).toBeTruthy();
    });
  });

  describe("live re-validation after first blur", () => {
    it("clears error when user corrects a touched field", async () => {
      const user = userEvent.setup();
      render(<MeasurementForm onSubmit={vi.fn()} />);
      const input = screen.getByLabelText(/full bust/i);
      // Type invalid, blur to mark touched
      await user.clear(input);
      await user.type(input, "59");
      await user.tab();
      expect(screen.getByText(/must be between/i)).toBeTruthy();
      // Click back on the field, fix it
      await user.clear(input);
      await user.type(input, "96");
      // Error should clear on change (live validation)
      await waitFor(() => {
        expect(screen.queryByText(/must be between/i)).toBeNull();
      });
    });
  });

  describe("submit behaviour", () => {
    it("submit button becomes enabled when all 7 fields have valid values", async () => {
      const user = userEvent.setup();
      render(<MeasurementForm onSubmit={vi.fn()} />);
      const btn = screen.getByRole("button", { name: /calculate my fit/i });
      expect(btn).toBeDisabled();
      for (const [label, value] of Object.entries(VALID_VALUES)) {
        const input = screen.getByLabelText(new RegExp(label, "i"));
        await user.clear(input);
        await user.type(input, value);
      }
      expect(btn).not.toBeDisabled();
    });

    it("calls onSubmit with correct Measurements when all fields are valid", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(<MeasurementForm onSubmit={onSubmit} />);

      for (const [label, value] of Object.entries(VALID_VALUES)) {
        const input = screen.getByLabelText(new RegExp(label, "i"));
        await user.clear(input);
        await user.type(input, value);
      }

      await user.click(screen.getByRole("button", { name: /calculate my fit/i }));

      expect(onSubmit).toHaveBeenCalledOnce();
      const arg = onSubmit.mock.calls[0][0];
      expect(arg.bust_cm).toBeCloseTo(96);
      expect(arg.high_bust_cm).toBeCloseTo(85);
      expect(arg.apex_to_apex_cm).toBeCloseTo(18);
      expect(arg.waist_cm).toBeCloseTo(78);
      expect(arg.hip_cm).toBeCloseTo(104);
      expect(arg.height_cm).toBeCloseTo(168);
      expect(arg.back_length_cm).toBeCloseTo(39.5);
    });
  });

  describe("isLoading prop", () => {
    it("disables all inputs when isLoading is true", () => {
      render(<MeasurementForm onSubmit={vi.fn()} isLoading />);
      FIELD_LABELS.forEach((label) => {
        expect(screen.getByLabelText(new RegExp(label, "i"))).toBeDisabled();
      });
    });

    it("disables submit button when isLoading is true", () => {
      render(<MeasurementForm onSubmit={vi.fn()} isLoading />);
      expect(screen.getByRole("button", { name: /calculate my fit/i })).toBeDisabled();
    });
  });

  describe("serverErrors prop", () => {
    it("displays a server error beneath the relevant field", () => {
      render(
        <MeasurementForm
          onSubmit={vi.fn()}
          serverErrors={{ bust_cm: "Server says no" }}
        />,
      );
      expect(screen.getByText("Server says no")).toBeTruthy();
    });

    it("clears server error when user edits the field", async () => {
      const user = userEvent.setup();
      render(
        <MeasurementForm
          onSubmit={vi.fn()}
          serverErrors={{ bust_cm: "Server says no" }}
        />,
      );
      expect(screen.getByText("Server says no")).toBeTruthy();
      const input = screen.getByLabelText(/full bust/i);
      await user.type(input, "1");
      await waitFor(() => {
        expect(screen.queryByText("Server says no")).toBeNull();
      });
    });
  });
});
