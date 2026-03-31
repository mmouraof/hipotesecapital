CREATE DATABASE HipoteseCapital;

CREATE TABLE Ativos (
    Ticker VARCHAR(255) NOT NULL,
    EmpresaAtivo VARCHAR(20) NOT NULL,
    SetorAtuacaoEmpresa VARCHAR(255) NOT NULL,
    SegmentoAtuacaoEmpresa VARCHAR(255) NOT NULL,
    ResumoEmpresa VARCHAR(2000) NOT NULL,
    PRIMARY KEY (Ticker)
);

CREATE TABLE DadosCotacao (
    IDConsulta INT NOT NULL,
    DataConsulta DATE NOT NULL,
    Ticker VARCHAR(20) NOT NULL,
    Cotacao DECIMAL(10, 2),
    DataUltimaCotacao DATE NOT NULL,
    Min52semanas DECIMAL(10, 2),
    Max52semanas DECIMAL(10, 2),
    VolumeMedio2Meses DECIMAL(20, 2),
    ValorMercado DECIMAL(30, 2),
    NumeroAcoes DECIMAL(35, 2),
    DataUltimoBalanco DATE NOT NULL,
    PRIMARY KEY (IDConsulta),
    FOREIGN KEY (Ticker) REFERENCES Ativos(Ticker)

);

CREATE TABLE IndicadoresFundamentalistas (
    IDConsulta INT NOT NULL,
    DataConsulta DATE NOT NULL,
    Ticker VARCHAR(20) NOT NULL,
    P_L DECIMAL(10, 2),
    ROE DECIMAL(10, 2),
    DividaLiquida_EBTIDA DECIMAL(10, 2),
    MargemLiquida DECIMAL(10, 2),
    DividendYield DECIMAL(10, 2),
    PRIMARY KEY (IDConsulta),
    FOREIGN KEY (Ticker) REFERENCES Ativos(Ticker)
);

CREATE TABLE Noticias (
    IDConsulta INT NOT NULL,
    DataConsulta DATE NOT NULL,
    Ticker VARCHAR(20) NOT NULL,
    URLNoticia VARCHAR(40) NOT NULL,
    Resumo VARCHAR(500) NOT NULL,
    Classificador VARCHAR(10) NOT NULL,
    Escala DECIMAL(5, 2) NOT NULL,
    PRIMARY KEY (IDConsulta, DataConsulta),
    FOREIGN KEY (Ticker) REFERENCES Ativos(Ticker)
)