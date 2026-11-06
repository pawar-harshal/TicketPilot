-- TicketPilot -- demo data (DEMO/STAGING ONLY -- never run in real production)
--
-- Table/database casing matches the SQLAlchemy models and config.ini
-- exactly (PascalCase) -- see the long comment at the top of
-- 01_structure.sql for why this matters on a Linux host.
--
-- Run this AFTER 01_structure.sql and 02_data.sql. It creates the 2 demo
-- customers used for every live demo (Rohan, Ananya), their 1 order
-- each, and the sp_reset_demo() stored procedure that resets both
-- orders' timing right before any demo.
--
-- This is deliberately kept out of 02_data.sql so a real production
-- deploy can run structure + data only, with zero fake customers in it.

USE `TicketPilot`;

-- ---------------------------------------------------------------------
-- Demo customers
-- ---------------------------------------------------------------------
-- Password for BOTH demo logins is: Customer@123
-- (shared bcrypt hash, copied verbatim from the 06-Nov-2026 backup)
INSERT INTO `Customer` (`C_Id`, `C_Name`, `C_Email`, `C_Phone`, `C_CreatedDate`, `C_PasswordHash`) VALUES
  (1, 'Rohan Deshmukh', 'rohan.deshmukh@example.com', '9876500001', '2026-09-01 10:00:00', '$2b$12$Hk8p8WOinEIIWT8rDNASCuQqC2G//ZDViRhGnDiTPYsvfM5txwziG'),
  (2, 'Ananya Iyer',    'ananya.iyer@example.com',    '9876500002', '2026-09-03 11:30:00', '$2b$12$Hk8p8WOinEIIWT8rDNASCuQqC2G//ZDViRhGnDiTPYsvfM5txwziG');

-- ---------------------------------------------------------------------
-- Demo orders -- exactly 1 per demo customer
-- ---------------------------------------------------------------------
-- Order #1 (Rohan) -- out for delivery, timing refreshed by sp_reset_demo.
-- Order #2 (Ananya) -- delivered, timing refreshed by sp_reset_demo.
-- O_ScenarioKey is left NULL here -- it is an optional manual tag, not
-- required for the reset procedure below (which addresses these two
-- orders directly by O_Id).
INSERT INTO `Order` (`O_Id`, `C_Id`, `O_Items`, `CUR_Id`, `O_TotalAmount`, `O_StatusId`, `O_OutForDeliveryDate`, `O_DeliveryEta`, `O_DeliveredDate`, `O_ScenarioKey`) VALUES
  (1, 1, '[{"qty": 1, "name": "Paneer Butter Masala"}, {"qty": 2, "name": "Butter Naan"}]', 1, 420.00, 2,
   DATE_SUB(NOW(), INTERVAL 55 MINUTE), DATE_SUB(NOW(), INTERVAL 10 MINUTE), NULL, NULL),
  (2, 2, '[{"qty": 1, "name": "Margherita Pizza"}, {"qty": 1, "name": "Garlic Bread"}]', 1, 560.00, 3,
   DATE_SUB(NOW(), INTERVAL 70 MINUTE), DATE_SUB(NOW(), INTERVAL 40 MINUTE), DATE_SUB(NOW(), INTERVAL 35 MINUTE), NULL);

-- ---------------------------------------------------------------------
-- sp_reset_demo() -- run this before every live demo
-- ---------------------------------------------------------------------
-- Wipes all ticket/message/approval history and re-times the two demo
-- orders relative to NOW(), without touching their items/total/status:
--   Order #1 (Rohan)  -> out_for_delivery, ETA ~10 minutes ago (late)
--   Order #2 (Ananya) -> delivered, ~35 minutes ago
DROP PROCEDURE IF EXISTS `sp_reset_demo`;

DELIMITER ;;
CREATE PROCEDURE `sp_reset_demo`()
BEGIN
    -- 1. Wipe all conversation history.
    DELETE FROM `Approval`;
    DELETE FROM `TicketMessage`;
    DELETE FROM `Ticket`;

    -- 2. Order #1 (Rohan) -- out for delivery, ~10 minutes late, right now.
    UPDATE `Order`
    SET `O_OutForDeliveryDate` = DATE_SUB(NOW(), INTERVAL 55 MINUTE),
        `O_DeliveryEta`       = DATE_SUB(NOW(), INTERVAL 10 MINUTE),
        `O_DeliveredDate`     = NULL
    WHERE `O_Id` = 1;

    -- 3. Order #2 (Ananya) -- delivered a little while ago, right now.
    UPDATE `Order`
    SET `O_OutForDeliveryDate` = DATE_SUB(NOW(), INTERVAL 70 MINUTE),
        `O_DeliveryEta`       = DATE_SUB(NOW(), INTERVAL 40 MINUTE),
        `O_DeliveredDate`     = DATE_SUB(NOW(), INTERVAL 35 MINUTE)
    WHERE `O_Id` = 2;
END ;;
DELIMITER ;

-- Run it once now so a fresh import is immediately demo-ready.
CALL sp_reset_demo();

-- ---------------------------------------------------------------------
-- Verify
-- ---------------------------------------------------------------------
SELECT c.C_Id, c.C_Name, c.C_Email, o.O_Id, o.O_TotalAmount, ost.OST_Name AS status,
       o.O_OutForDeliveryDate, o.O_DeliveryEta, o.O_DeliveredDate
FROM `Customer` c
JOIN `Order` o ON o.C_Id = c.C_Id
JOIN `OrderStatusType` ost ON ost.OST_Id = o.O_StatusId
ORDER BY c.C_Id;
