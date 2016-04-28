CREATE TABLE `cdn_domain_manager_cdnbillmethod` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `tenant_id` varchar(64) NOT NULL,
    `current_type` varchar(20) NOT NULL,
    `update_type` varchar(20),
    `update_at` datetime,
    `effect_at` datetime
)
;
CREATE TABLE `cdn_domain_manager_domain` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `tenant_id` varchar(64) NOT NULL,
    `user_name` varchar(64) NOT NULL,
    `project_name` varchar(64) NOT NULL,
    `domain_id` varchar(64),
    `domain_name` varchar(64) NOT NULL,
    `domain_cname` varchar(64),
    `source_type` varchar(64),
    `status` varchar(20) NOT NULL,
    `Enable` varchar(10) NOT NULL,
    `current_type` varchar(20) NOT NULL,
    `update_type` varchar(20),
    `created_at` datetime NOT NULL,
    `deleted_at` datetime,
    `update_at` datetime,
    `effect_at` datetime,
    `error_log` longtext,
    `xCncRequestId` varchar(64)
)
;
CREATE TABLE `cdn_domain_manager_sourceaddress` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `domain_id` integer NOT NULL,
    `source_address` varchar(64) NOT NULL
)
;
ALTER TABLE `cdn_domain_manager_sourceaddress` ADD CONSTRAINT `domain_id_refs_id_3d251825` FOREIGN KEY (`domain_id`) REFERENCES `cdn_domain_manager_domain` (`id`);
CREATE TABLE `cdn_domain_manager_cacherule` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `domain_id` integer NOT NULL,
    `pathPattern` varchar(64) NOT NULL,
    `ignoreCacheControl` bool NOT NULL,
    `cacheTtl` varchar(64) NOT NULL
)
;
ALTER TABLE `cdn_domain_manager_cacherule` ADD CONSTRAINT `domain_id_refs_id_8967b4d0` FOREIGN KEY (`domain_id`) REFERENCES `cdn_domain_manager_domain` (`id`);
CREATE TABLE `cdn_domain_manager_accesscontrol` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `domain_id` integer NOT NULL,
    `pathPattern` varchar(64) NOT NULL,
    `allowNullReffer` bool NOT NULL,
    `validRefers` varchar(128) NOT NULL,
    `invalidRefers` varchar(128) NOT NULL,
    `forbiddenIps` varchar(128) NOT NULL
)
;
ALTER TABLE `cdn_domain_manager_accesscontrol` ADD CONSTRAINT `domain_id_refs_id_f0114c65` FOREIGN KEY (`domain_id`) REFERENCES `cdn_domain_manager_domain` (`id`);
CREATE INDEX `cdn_domain_manager_sourceaddress_e8b327e7` ON `cdn_domain_manager_sourceaddress` (`domain_id`);
CREATE INDEX `cdn_domain_manager_cacherule_e8b327e7` ON `cdn_domain_manager_cacherule` (`domain_id`);
CREATE INDEX `cdn_domain_manager_accesscontrol_e8b327e7` ON `cdn_domain_manager_accesscontrol` (`domain_id`);
CREATE TABLE `cdn_cache_refresh_cacherule` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cache_type` varchar(64) NOT NULL,
    `cache_time` integer NOT NULL,
    `status` varchar(64) NOT NULL
)
;



