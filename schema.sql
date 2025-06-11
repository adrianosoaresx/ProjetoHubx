BEGIN;
--
-- Create model Tag
--
CREATE TABLE "empresas_tag" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nome" varchar(50) NOT NULL UNIQUE);
--
-- Create model Empresa
--
CREATE TABLE "empresas_empresa" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "cnpj" varchar(18) NOT NULL UNIQUE, "nome" varchar(255) NOT NULL, "tipo" varchar(100) NOT NULL, "municipio" varchar(100) NOT NULL, "estado" varchar(2) NOT NULL, "logo" varchar(100) NULL, "descricao" text NOT NULL, "contato" varchar(255) NOT NULL, "palavras_chave" varchar(255) NOT NULL, "usuario_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "empresas_empresa_tags" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "empresa_id" bigint NOT NULL REFERENCES "empresas_empresa" ("id") DEFERRABLE INITIALLY DEFERRED, "tag_id" bigint NOT NULL REFERENCES "empresas_tag" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX "empresas_empresa_usuario_id_9792304b" ON "empresas_empresa" ("usuario_id");
CREATE UNIQUE INDEX "empresas_empresa_tags_empresa_id_tag_id_64fb4981_uniq" ON "empresas_empresa_tags" ("empresa_id", "tag_id");
CREATE INDEX "empresas_empresa_tags_empresa_id_6657ffad" ON "empresas_empresa_tags" ("empresa_id");
CREATE INDEX "empresas_empresa_tags_tag_id_8ee66831" ON "empresas_empresa_tags" ("tag_id");
COMMIT;

BEGIN;
--
-- Create model NotificationSettings
--
CREATE TABLE "perfil_notificationsettings" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "email_conexoes" bool NOT NULL, "email_mensagens" bool NOT NULL, "email_eventos" bool NOT NULL, "email_newsletter" bool NOT NULL, "sistema_conexoes" bool NOT NULL, "sistema_mensagens" bool NOT NULL, "sistema_eventos" bool NOT NULL, "sistema_comentarios" bool NOT NULL, "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Perfil
--
CREATE TABLE "perfil_perfil" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "avatar" varchar(100) NULL, "bio" text NOT NULL, "data_nascimento" date NULL, "genero" varchar(1) NOT NULL, "telefone" varchar(20) NOT NULL, "whatsapp" varchar(20) NOT NULL, "endereco" varchar(255) NOT NULL, "cidade" varchar(100) NOT NULL, "estado" varchar(2) NOT NULL, "cep" varchar(10) NOT NULL, "facebook" varchar(200) NOT NULL, "twitter" varchar(200) NOT NULL, "instagram" varchar(200) NOT NULL, "linkedin" varchar(200) NOT NULL, "website" varchar(200) NOT NULL, "idioma" varchar(10) NOT NULL, "fuso_horario" varchar(50) NOT NULL, "perfil_publico" bool NOT NULL, "mostrar_email" bool NOT NULL, "mostrar_telefone" bool NOT NULL, "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
COMMIT;

