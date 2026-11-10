-- Results of the chatbot QA runs. Database ChatbotQA on the local SQL Server (Windows login), separate from every other database.
-- Only run results are stored: no keys, no passwords, and no transcript of the made-up child identity (PRV / MEM).
IF DB_ID(N'ChatbotQA') IS NULL CREATE DATABASE ChatbotQA;
GO
USE ChatbotQA;
GO
IF OBJECT_ID(N'dbo.qa_runs') IS NULL
CREATE TABLE dbo.qa_runs (
  run_id        INT IDENTITY PRIMARY KEY,
  started_at    DATETIME2 NOT NULL,
  duration_s    FLOAT NULL,
  report_file   NVARCHAR(260) NULL,
  backend_base  NVARCHAR(200) NULL,
  chat_mode     NVARCHAR(20) NULL,
  chat_runs     INT NULL,
  stories       NVARCHAR(100) NULL
);
GO
IF OBJECT_ID(N'dbo.qa_results') IS NULL
CREATE TABLE dbo.qa_results (
  result_id  INT IDENTITY PRIMARY KEY,
  run_id     INT NOT NULL REFERENCES dbo.qa_runs(run_id),
  story      NVARCHAR(10) NOT NULL,
  criterion  NVARCHAR(40) NULL,
  test_name  NVARCHAR(400) NOT NULL,
  outcome    NVARCHAR(20) NOT NULL,
  duration   NVARCHAR(20) NULL,
  message    NVARCHAR(MAX) NULL,
  note       NVARCHAR(MAX) NULL,
  transcript NVARCHAR(MAX) NULL
);
GO
