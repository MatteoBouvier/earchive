pub mod dedup;
pub mod progress;

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, Clone)]
pub enum Error {
    GeneralError(String),
    HashError(String),
    ThreadError(String),
}

impl From<std::io::Error> for Error {
    fn from(value: std::io::Error) -> Self {
        Self::GeneralError(value.to_string())
    }
}
