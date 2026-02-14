-- Defense-in-depth: prevent negative credit balances at the database level.
-- The application checks balance before deduction, but concurrent requests
-- could race past the check. This constraint makes the DB reject the second
-- conflicting UPDATE, which the application handles as a CreditServiceError.

ALTER TABLE credits
  ADD CONSTRAINT credits_remaining_non_negative CHECK (credits_remaining >= 0);
