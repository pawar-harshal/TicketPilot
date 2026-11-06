-- TicketPilot -- master/lookup data (NOT demo data)
--
-- Table/database casing matches the SQLAlchemy models and config.ini
-- exactly (PascalCase) -- see the long comment at the top of
-- 01_structure.sql for why this matters on a Linux host.
--
-- Run this on EVERY environment (dev, staging, production) right after
-- 01_structure.sql. It seeds only what the application itself needs to
-- function: the lookup/enum tables, the real knowledge-base policy
-- articles, and the one support-manager login. It contains NO demo
-- customers or demo orders -- those live in 03_demo_data.sql and should
-- only be run in a demo/staging environment.
--
-- The lookup-table names/values below MUST stay byte-for-byte identical
-- to the matching enums in ticketpilot_das/utils/CommonEnums.py
-- (ApprovalActionType, ApprovalStatusType, MessageSenderType,
-- OrderStatus, TicketStatus, CurrencyCode) -- the app's cache modules
-- resolve these names to ids at startup and raise an error if a name
-- used in code was never seeded here.

USE `TicketPilot`;

-- ---------------------------------------------------------------------
-- Currency
-- ---------------------------------------------------------------------
INSERT INTO `Currency` (`CUR_Id`, `CUR_Code`, `CUR_Name`, `CUR_Symbol`) VALUES
  (1, 'INR', 'Indian Rupee', '₹');

-- ---------------------------------------------------------------------
-- ApprovalActionType
-- ---------------------------------------------------------------------
INSERT INTO `ApprovalActionType` (`APAT_Id`, `APAT_Name`) VALUES
  (1, 'refund'),
  (2, 'credit');

-- ---------------------------------------------------------------------
-- ApprovalStatusType
-- ---------------------------------------------------------------------
INSERT INTO `ApprovalStatusType` (`APST_Id`, `APST_Name`) VALUES
  (1, 'pending'),
  (2, 'approved'),
  (3, 'rejected');

-- ---------------------------------------------------------------------
-- MessageSenderType
-- ---------------------------------------------------------------------
INSERT INTO `MessageSenderType` (`MST_Id`, `MST_Name`) VALUES
  (1, 'customer'),
  (2, 'agent'),
  (3, 'system');

-- ---------------------------------------------------------------------
-- OrderStatusType
-- ---------------------------------------------------------------------
INSERT INTO `OrderStatusType` (`OST_Id`, `OST_Name`) VALUES
  (1, 'placed'),
  (2, 'out_for_delivery'),
  (3, 'delivered'),
  (4, 'cancelled');

-- ---------------------------------------------------------------------
-- TicketStatusType
-- ---------------------------------------------------------------------
INSERT INTO `TicketStatusType` (`TST_Id`, `TST_Name`) VALUES
  (1, 'investigating'),
  (2, 'resolved'),
  (3, 'escalated'),
  (4, 'pending_approval'),
  (5, 'awaiting_customer');

-- ---------------------------------------------------------------------
-- KnowledgeBaseArticle -- real policy content, used by search_knowledge_base
-- ---------------------------------------------------------------------
INSERT INTO `KnowledgeBaseArticle` (`KBA_Id`, `KBA_Title`, `KBA_Content`, `KBA_EmbeddingSynced`) VALUES
  (1, 'Late or missing delivery',
   'If your order has not arrived by its estimated delivery time, please wait up to 20 minutes past the ETA before contacting support, as traffic and weather can cause short delays. If the order is more than 30 minutes late or marked delivered but never received, our team can issue a refund or credit after confirming the order status with the courier.',
   0),
  (2, 'How refunds are processed',
   'Approved refunds are issued to the original payment method and typically appear within 5-7 business days. Store credit is applied to your account immediately and can be used on your next order.',
   0),
  (3, 'Changing or cancelling an order',
   'Orders can be changed or cancelled only before the restaurant marks them as being prepared. Once preparation has started, the order cannot be changed and must be handled as a delivery issue instead.',
   0),
  (4, 'Missing or incorrect items',
   'If part of your order is missing, or you received the wrong item, we can issue a partial refund or credit for the affected item(s) once the order\'s contents have been checked against what was ordered. A full refund is not automatic for a partial problem -- only the affected item(s), not the whole order.',
   0),
  (5, 'Order cancelled by the restaurant',
   'If a restaurant cancels your order before it is prepared (status shows cancelled), you are entitled to a full refund of the order total. No partial refund applies in this case since nothing was delivered.',
   0),
  (6, 'Delivered significantly late',
   'If an order is delivered more than 30 minutes past its estimated delivery time, food quality may be affected by the extra time in transit. In that case a partial credit can be issued to acknowledge the delay, separate from (and smaller than) a full refund for an order that was never delivered at all.',
   0);

-- NOTE: KBA_EmbeddingSynced is seeded as 0 (not yet indexed in Qdrant) on
-- purpose -- the app's own startup/sync job is what should flip these to
-- 1 once it has actually embedded and indexed each article, not this
-- script. Do not hand-set this to 1.

-- ---------------------------------------------------------------------
-- User -- the one support-manager login
-- ---------------------------------------------------------------------
-- Password hash below is the REAL bcrypt hash currently in production
-- for harshal.pawar@quickcrave.com, copied verbatim from the 06-Nov-2026
-- backup. If you need a different password on a new environment,
-- generate a fresh bcrypt hash (e.g. via the backend's own auth helper)
-- and replace it here -- never hand-write a hash.
INSERT INTO `User` (`U_Id`, `U_Email`, `U_PasswordHash`, `U_Role`, `U_CreatedDate`) VALUES
  (1, 'harshal.pawar@quickcrave.com', '$2b$12$S8jTQA5Al1rw.rJn6SvcTeACtsqu7td6l6RAkm.rl2aB2oWXCJIvO', 'support_manager', '2026-09-01 09:00:00');
