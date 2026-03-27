import { SAMPLE_TRANSACTIONS } from "./sample-data";

describe("SAMPLE_TRANSACTIONS", () => {
  it("has 10 transactions", () => {
    expect(SAMPLE_TRANSACTIONS).toHaveLength(10);
  });

  it("each transaction has required fields", () => {
    for (const txn of SAMPLE_TRANSACTIONS) {
      expect(txn).toHaveProperty("date");
      expect(txn).toHaveProperty("description");
      expect(txn).toHaveProperty("amount");
      expect(txn).toHaveProperty("category");
      expect(typeof txn.date).toBe("string");
      expect(typeof txn.description).toBe("string");
      expect(typeof txn.amount).toBe("number");
    }
  });

  it("all categories start empty", () => {
    for (const txn of SAMPLE_TRANSACTIONS) {
      expect(txn.category).toBe("");
    }
  });
});
