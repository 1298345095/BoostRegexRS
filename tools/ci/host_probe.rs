//! Record the architecture of a program actually executed on the CI host.
fn main() {
    println!(
        "{{\"architecture\":\"{}\",\"os\":\"{}\",\"pointer_bits\":{}}}",
        std::env::consts::ARCH,
        std::env::consts::OS,
        usize::BITS
    );
}
