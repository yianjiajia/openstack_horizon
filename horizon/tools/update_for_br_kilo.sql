ALTER TABLE `cdn_domain_manager_domain` CHANGE `create_time` `created_at` datetime NOT NULL;
ALTER TABLE `cdn_domain_manager_domain` ADD `update_at` datetime AFTER `Enable`;
ALTER TABLE `cdn_domain_manager_domain` ADD `current_type` varchar(16)  AFTER `update_at`;
ALTER TABLE `cdn_domain_manager_domain` ADD `update_type` varchar(16)  AFTER `current_type`;
ALTER TABLE `cdn_domain_manager_domain` ADD `effect_at` datetime AFTER `update_type`;
ALTER TABLE `cdn_domain_manager_domain` ADD `error_log` longtext AFTER `effect_at`;
ALTER TABLE `cdn_domain_manager_domain` ADD `deleted_at` datetime  AFTER `error_log`;
ALTER TABLE `cdn_domain_manager_domain` ADD `user_name` varchar(64)  AFTER `tenant_id`;
ALTER TABLE `cdn_domain_manager_domain` ADD `project_name` varchar(64)  AFTER `user_name`;
ALTER TABLE `cdn_domain_manager_domain` ADD `xCncRequestId` varchar(64)  AFTER `error_log`;

