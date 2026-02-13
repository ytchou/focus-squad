-- Migration: 033_drop_obsolete_refund_rpc.sql
-- Description: Remove add_essence function that was made obsolete by
-- migration 031's atomic purchase_item_atomic RPC.
-- The atomic RPC handles both essence deduction and inventory insertion
-- in a single transaction, eliminating the need for compensating refunds.

DROP FUNCTION IF EXISTS add_essence(UUID, INTEGER);
