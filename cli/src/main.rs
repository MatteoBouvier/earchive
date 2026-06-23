use std::{
    fs,
    path::{Path, PathBuf},
};

use clap::Parser;
use tools::dedup::deduplicate;

#[derive(Parser)]
#[command(name = "earchive")]
#[command(version = "0.1")]
#[command(about="Set of tools for working with digital archives", long_about=None)]
struct Cli {
    /// first directory to compare
    dir_1: PathBuf,

    /// second directory to compare
    dir_2: PathBuf,

    /// number of threads
    #[arg(default_value_t = 1)]
    n_threads: u8,
}

fn main() {
    let cli = Cli::parse();

    let dir_1 = match fs::canonicalize(Path::new(&cli.dir_1)) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("Failed to canonicalize path dir_1: {}", e);
            std::process::exit(1);
        }
    };
    let dir_2 = match fs::canonicalize(Path::new(&cli.dir_2)) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("Failed to canonicalize path dir_2: {}", e);
            std::process::exit(1);
        }
    };

    match deduplicate(&dir_1, &dir_2, cli.n_threads) {
        Ok(_) => std::process::exit(0),
        Err(e) => {
            println!("{e:?}");
            std::process::exit(1);
        }
    }
}
