# Host: 127.0.0.1  (Version 5.7.16-log)
# Date: 2021-10-28 16:24:48
# Generator: MySQL-Front 5.4  (Build 3.52)
# Internet: http://www.mysqlfront.de/

/*!40101 SET NAMES utf8 */;

#
# Structure for table "guanchazhe"
#

DROP TABLE IF EXISTS `guanchazhe`;
CREATE TABLE `guanchazhe` (
  `Id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) DEFAULT NULL,
  `author` varchar(255) DEFAULT NULL,
  `publish_time` varchar(255) DEFAULT NULL,
  `content` longtext,
  `url` varchar(255) DEFAULT NULL,
  `key_word` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB AUTO_INCREMENT=414 DEFAULT CHARSET=utf8;

#
# Data for table "guanchazhe"
#