-- TicketPilot -- database structure (schema only, no data)
--
-- IMPORTANT -- table/database casing:
-- This matches EXACTLY what the SQLAlchemy models actually declare
-- (ticket_management/entity/DbModels.py, auth/entity/DbModels.py,
-- approval_engine/entity/DbModels.py -- every __tablename__ is
-- PascalCase) and what data/config.ini's database_name is set to
-- ("TicketPilot", also PascalCase).
--
-- On the current Windows dev machine, MySQL runs with
-- lower_case_table_names=1 (Windows default), which silently lowercases
-- every table/database name on disk and makes lookups case-INsensitive
-- -- so a full backup taken there shows `ticketpilot`, `customer`,
-- `order`, etc. in lowercase even though the code says "TicketPilot",
-- "Customer", "Order". That lowercase casing is a Windows-only artifact,
-- NOT the real schema.
--
-- Most Linux hosts (the usual hosting target) run MySQL with
-- lower_case_table_names=0 (verified against a real MySQL/MariaDB
-- instance while building this script) -- table and database names are
-- CASE-SENSITIVE there. If this script used lowercase names, every
-- SQLAlchemy query (which asks for "Customer", "Order", etc. verbatim)
-- would fail with "Table 'ticketpilot.Customer' doesn't exist" the
-- moment you moved off Windows. So every name below is PascalCase,
-- byte-for-byte matching the Python models -- this is what actually
-- works cross-platform, not a copy of the Windows dump's casing.
--
-- Run this FIRST on a fresh database, before 02_data.sql.
-- Run 03_demo_data.sql afterwards ONLY in a demo/staging environment --
-- never in real production.
--
-- NOTE: config.ini has `auto_create_tables = true`, which makes the
-- backend call SQLAlchemy's Base.metadata.create_all() on every
-- startup -- it will create any of these tables itself if they don't
-- already exist (same casing, since it reads it straight from the
-- models). Running this script first is still recommended for a
-- production deploy (explicit, reviewable, no surprise schema changes
-- from just starting the app) but is not strictly required.

CREATE DATABASE IF NOT EXISTS `TicketPilot`
  /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */;
USE `TicketPilot`;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- Lookup / master tables (no foreign keys out) -- create first
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS `Currency`;
CREATE TABLE `Currency` (
  `CUR_Id` bigint NOT NULL AUTO_INCREMENT,
  `CUR_Code` varchar(10) NOT NULL,
  `CUR_Name` varchar(50) NOT NULL,
  `CUR_Symbol` varchar(5) NOT NULL,
  PRIMARY KEY (`CUR_Id`),
  UNIQUE KEY `CUR_Id_UNIQUE` (`CUR_Id`),
  UNIQUE KEY `CUR_Code_UNIQUE` (`CUR_Code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `ApprovalActionType`;
CREATE TABLE `ApprovalActionType` (
  `APAT_Id` bigint NOT NULL AUTO_INCREMENT,
  `APAT_Name` varchar(20) NOT NULL,
  PRIMARY KEY (`APAT_Id`),
  UNIQUE KEY `APAT_Id_UNIQUE` (`APAT_Id`),
  UNIQUE KEY `APAT_Name_UNIQUE` (`APAT_Name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `ApprovalStatusType`;
CREATE TABLE `ApprovalStatusType` (
  `APST_Id` bigint NOT NULL AUTO_INCREMENT,
  `APST_Name` varchar(20) NOT NULL,
  PRIMARY KEY (`APST_Id`),
  UNIQUE KEY `APST_Id_UNIQUE` (`APST_Id`),
  UNIQUE KEY `APST_Name_UNIQUE` (`APST_Name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `MessageSenderType`;
CREATE TABLE `MessageSenderType` (
  `MST_Id` bigint NOT NULL AUTO_INCREMENT,
  `MST_Name` varchar(20) NOT NULL,
  PRIMARY KEY (`MST_Id`),
  UNIQUE KEY `MST_Id_UNIQUE` (`MST_Id`),
  UNIQUE KEY `MST_Name_UNIQUE` (`MST_Name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `OrderStatusType`;
CREATE TABLE `OrderStatusType` (
  `OST_Id` bigint NOT NULL AUTO_INCREMENT,
  `OST_Name` varchar(30) NOT NULL,
  PRIMARY KEY (`OST_Id`),
  UNIQUE KEY `OST_Id_UNIQUE` (`OST_Id`),
  UNIQUE KEY `OST_Name_UNIQUE` (`OST_Name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `TicketStatusType`;
CREATE TABLE `TicketStatusType` (
  `TST_Id` bigint NOT NULL AUTO_INCREMENT,
  `TST_Name` varchar(30) NOT NULL,
  PRIMARY KEY (`TST_Id`),
  UNIQUE KEY `TST_Id_UNIQUE` (`TST_Id`),
  UNIQUE KEY `TST_Name_UNIQUE` (`TST_Name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `KnowledgeBaseArticle`;
CREATE TABLE `KnowledgeBaseArticle` (
  `KBA_Id` bigint NOT NULL AUTO_INCREMENT,
  `KBA_Title` varchar(255) NOT NULL,
  `KBA_Content` text NOT NULL,
  `KBA_EmbeddingSynced` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`KBA_Id`),
  UNIQUE KEY `KBA_Id_UNIQUE` (`KBA_Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Entity tables with no, or only lookup-table, foreign keys
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS `Customer`;
CREATE TABLE `Customer` (
  `C_Id` bigint NOT NULL AUTO_INCREMENT,
  `C_Name` varchar(255) NOT NULL,
  `C_Email` varchar(255) NOT NULL,
  `C_Phone` varchar(20) NOT NULL,
  `C_CreatedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `C_PasswordHash` varchar(255) DEFAULT NULL COMMENT 'Bcrypt hash for customer login. NULL for any legacy row created before customer login existed.',
  PRIMARY KEY (`C_Id`),
  UNIQUE KEY `C_Id_UNIQUE` (`C_Id`),
  UNIQUE KEY `C_Email_UNIQUE` (`C_Email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `User`;
CREATE TABLE `User` (
  `U_Id` bigint NOT NULL AUTO_INCREMENT,
  `U_Email` varchar(255) NOT NULL,
  `U_PasswordHash` varchar(255) NOT NULL,
  `U_Role` varchar(30) NOT NULL DEFAULT 'support_manager',
  `U_CreatedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`U_Id`),
  UNIQUE KEY `U_Id_UNIQUE` (`U_Id`),
  UNIQUE KEY `U_Email_UNIQUE` (`U_Email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Order -- depends on Customer, Currency, OrderStatusType
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS `Order`;
CREATE TABLE `Order` (
  `O_Id` bigint NOT NULL AUTO_INCREMENT,
  `C_Id` bigint NOT NULL,
  `O_Items` json NOT NULL,
  `CUR_Id` bigint NOT NULL,
  `O_TotalAmount` decimal(10,2) NOT NULL,
  `O_StatusId` bigint NOT NULL,
  `O_OutForDeliveryDate` datetime DEFAULT NULL,
  `O_DeliveryEta` datetime DEFAULT NULL,
  `O_DeliveredDate` datetime DEFAULT NULL,
  `O_ScenarioKey` varchar(50) DEFAULT NULL COMMENT 'OPTIONAL, manually-set, TIMING-ONLY tag. Never written by request-time code. When set to a key in DemoScenario.SCENARIO_TEMPLATES, ensure_order_fresh() recomputes O_OutForDeliveryDate/O_DeliveryEta/O_DeliveredDate relative to NOW() so a demo order always looks freshly timed -- it NEVER touches O_StatusId, O_Items or O_TotalAmount, which are real data. Leave NULL for any real/non-demo order.',
  PRIMARY KEY (`O_Id`),
  UNIQUE KEY `O_Id_UNIQUE` (`O_Id`),
  KEY `fk_Order_Customer_idx` (`C_Id`),
  KEY `fk_Order_Currency_idx` (`CUR_Id`),
  KEY `fk_Order_OrderStatusType_idx` (`O_StatusId`),
  CONSTRAINT `fk_Order_Currency` FOREIGN KEY (`CUR_Id`) REFERENCES `Currency` (`CUR_Id`),
  CONSTRAINT `fk_Order_Customer` FOREIGN KEY (`C_Id`) REFERENCES `Customer` (`C_Id`),
  CONSTRAINT `fk_Order_OrderStatusType` FOREIGN KEY (`O_StatusId`) REFERENCES `OrderStatusType` (`OST_Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Ticket -- depends on Customer, Order, TicketStatusType
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS `Ticket`;
CREATE TABLE `Ticket` (
  `T_Id` bigint NOT NULL AUTO_INCREMENT,
  `C_Id` bigint NOT NULL,
  `O_Id` bigint NOT NULL,
  `T_StatusId` bigint NOT NULL,
  `T_InvestigationTrail` json DEFAULT NULL,
  `T_CreatedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `T_ResolvedDate` datetime DEFAULT NULL,
  PRIMARY KEY (`T_Id`),
  UNIQUE KEY `T_Id_UNIQUE` (`T_Id`),
  KEY `fk_Ticket_Customer_idx` (`C_Id`),
  KEY `fk_Ticket_Order_idx` (`O_Id`),
  KEY `fk_Ticket_TicketStatusType_idx` (`T_StatusId`),
  CONSTRAINT `fk_Ticket_Customer` FOREIGN KEY (`C_Id`) REFERENCES `Customer` (`C_Id`),
  CONSTRAINT `fk_Ticket_Order` FOREIGN KEY (`O_Id`) REFERENCES `Order` (`O_Id`),
  CONSTRAINT `fk_Ticket_TicketStatusType` FOREIGN KEY (`T_StatusId`) REFERENCES `TicketStatusType` (`TST_Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- TicketMessage -- depends on Ticket, MessageSenderType
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS `TicketMessage`;
CREATE TABLE `TicketMessage` (
  `TM_Id` bigint NOT NULL AUTO_INCREMENT,
  `T_Id` bigint NOT NULL,
  `TM_SenderId` bigint NOT NULL,
  `TM_Message` text NOT NULL,
  `TM_CreatedDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`TM_Id`),
  UNIQUE KEY `TM_Id_UNIQUE` (`TM_Id`),
  KEY `fk_TicketMessage_Ticket_idx` (`T_Id`,`TM_CreatedDate`),
  KEY `fk_TicketMessage_MessageSenderType_idx` (`TM_SenderId`),
  CONSTRAINT `fk_TicketMessage_MessageSenderType` FOREIGN KEY (`TM_SenderId`) REFERENCES `MessageSenderType` (`MST_Id`),
  CONSTRAINT `fk_TicketMessage_Ticket` FOREIGN KEY (`T_Id`) REFERENCES `Ticket` (`T_Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Approval -- depends on Ticket, ApprovalActionType, Currency,
-- ApprovalStatusType, User
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS `Approval`;
CREATE TABLE `Approval` (
  `AP_Id` bigint NOT NULL AUTO_INCREMENT,
  `T_Id` bigint NOT NULL,
  `APAT_Id` bigint NOT NULL,
  `AP_Amount` decimal(10,2) NOT NULL,
  `CUR_Id` bigint NOT NULL,
  `AP_Reason` text NOT NULL,
  `APST_Id` bigint NOT NULL,
  `AP_ApproverId` bigint DEFAULT NULL,
  `AP_DecidedDate` datetime DEFAULT NULL,
  PRIMARY KEY (`AP_Id`),
  UNIQUE KEY `AP_Id_UNIQUE` (`AP_Id`),
  KEY `fk_Approval_Ticket_idx` (`T_Id`),
  KEY `fk_Approval_ApprovalActionType_idx` (`APAT_Id`),
  KEY `fk_Approval_Currency_idx` (`CUR_Id`),
  KEY `fk_Approval_ApprovalStatusType_idx` (`APST_Id`),
  KEY `fk_Approval_User_idx` (`AP_ApproverId`),
  CONSTRAINT `fk_Approval_ApprovalActionType` FOREIGN KEY (`APAT_Id`) REFERENCES `ApprovalActionType` (`APAT_Id`),
  CONSTRAINT `fk_Approval_ApprovalStatusType` FOREIGN KEY (`APST_Id`) REFERENCES `ApprovalStatusType` (`APST_Id`),
  CONSTRAINT `fk_Approval_Currency` FOREIGN KEY (`CUR_Id`) REFERENCES `Currency` (`CUR_Id`),
  CONSTRAINT `fk_Approval_Ticket` FOREIGN KEY (`T_Id`) REFERENCES `Ticket` (`T_Id`),
  CONSTRAINT `fk_Approval_User` FOREIGN KEY (`AP_ApproverId`) REFERENCES `User` (`U_Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
