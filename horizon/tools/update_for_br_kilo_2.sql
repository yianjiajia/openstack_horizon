ALTER TABLE `cdn_domain_manager_domain` MODIFY `current_type` varchar(20);
ALTER TABLE `cdn_domain_manager_domain` MODIFY `update_type` varchar(20);

CREATE TABLE `cdn_domain_manager_cdnbillmethod` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `tenant_id` varchar(64) NOT NULL,
    `current_type` varchar(20) NOT NULL,
    `update_type` varchar(20),
    `update_at` datetime,
    `effect_at` datetime
)
;
